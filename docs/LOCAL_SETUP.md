# Local setup

## Complete core path

Docker Engine/Desktop and Docker Compose v2 with `--wait`, Python 3 for secret bootstrap, and Git. Node/Python application dependencies are built inside containers. The default core uses web, API, PostgreSQL and a worker; one short-lived migration/seed job runs first.

```bash
git clone https://github.com/subhanjandas/maple-harbour-bank.git
cd maple-harbour-bank
python3 scripts/bootstrap.py
docker compose up --build -d --wait --wait-timeout 180
curl --fail http://localhost:8080/api/health/ready
```

Open `http://localhost:8080`. The default seeds Subhanjan/Sam (customers), Taylor (Toronto operations), Morgan (Vancouver operations), Jordan (analyst) and Casey (engineer). Only selected personas are shown in the app. All records and funds are synthetic. The development selector is intentionally not production OIDC.

The migration runner applies checksum-verified forward SQL and rejects modified or unknown migrations. It creates separate no-login service roles; the bootstrap creates distinct login credentials. The API never uses the schema-owner credential. Funding is idempotent: restarting/migrating does not reset balances or duplicate opening journals.

Only web port 8080 is published, on loopback. Use `docker compose exec db psql -U postgres -d mhb` for local operator inspection. API and database are reachable only through the Compose network by default. The PostgreSQL 18 volume path is `/var/lib/postgresql`.

## Resource profiles

| Profile | Runnable now? | What starts | Resource guidance |
|---|---|---|---|
| Core development | Yes, default Compose | React/nginx, FastAPI, PostgreSQL, polling worker | Start with 2+ CPUs and 4GB Docker VM RAM; allow build/disk headroom. Idle sample is in performance evidence; this is not an empirically established minimum. |
| Data platform | Planned, no fake startup claim | Later CDC/Kafka group, Spark/Delta group and orchestration group | Budget separately; do not start all on the assumption they fit in 8GB Docker RAM. Validate grouped 16–32GB lab configurations before prescribing a minimum. |
| Public demo | Not yet deployed | Persistent core, OIDC/TLS, isolated scenarios, approved serving | Smaller than target lakehouse, explicitly labelled. Needs security and budget gates. |
| Scale/resilience lab | Bounded isolated core lab exists | Separate Compose project plus benchmark job; no multi-node HA | 4-vCPU/16GB CI baseline recorded; larger topology remains untested. |

Docker memory limits total roughly 2.1GiB across runtime services; building images and the Docker VM need additional memory. Limits are caps, not measured idle consumption. Stop unnecessary containers on the 16GB laptop; the core is the intended starting profile.

## Native developer/test path

Python 3.12, Node 22.12+ (CI uses Node 24), uv 0.12.23 and a reachable PostgreSQL 18 instance. Create a dedicated database; never aim tests at a database with valuable records because fixtures truncate its application tables.

```bash
uv sync --project backend --frozen
npm ci --prefix web
# Supply MIGRATION_DATABASE_URL, API_PASSWORD, WORKER_PASSWORD from a secret store/environment.
cd backend
uv run python -m mhb.migrate
uv run python ../scripts/create_service_users.py
uv run python -m mhb.seed
# Set DATABASE_URL to the API login, SESSION_SECRET (random 32+ chars),
# APP_ORIGIN=http://localhost:5173 and DEMO_AUTH=true for loopback development.
uv run uvicorn mhb.asgi:app --host 127.0.0.1 --port 8000 --no-access-log
```

In separate terminals, `uv run python -m mhb.pipeline` from `backend/` with `WORKER_DATABASE_URL`, and `npm run dev --prefix web`. Vite proxies `/api` to port 8000. Do not place database URLs or session secrets in frontend/Vite variables.

```bash
cd backend
TEST_DATABASE_URL='postgresql://<dedicated-test-owner>@localhost/<dedicated-test-db>' uv run pytest -q
# From web/ with actual API/worker running and APP_ORIGIN=http://localhost:5173:
npm run test:e2e
```

Tests without `TEST_DATABASE_URL` skip integration checks and are not equivalent to acceptance. CI supplies real PostgreSQL, exercises separate login roles, uses actual HTTP browser flows and starts the container profile.

## Isolated scale lab

```bash
# Repository root; do not use an existing public application database.
SOURCE_COMMIT=$(git rev-parse HEAD) LAB_UID=$(id -u) LAB_GID=$(id -g) \
  docker compose -p mhb-scale-lab -f compose.yaml -f infra/compose.lab.yaml --profile lab run --rm benchmark
# Stop the isolated project's services while preserving its named volume:
SOURCE_COMMIT=$(git rev-parse HEAD) docker compose -p mhb-scale-lab -f compose.yaml -f infra/compose.lab.yaml down
```

The job records source-record query measurements separately from actual payment commands in `evidence/lab-benchmark.json`. It raises the API request threshold only in the isolated lab, not the core or public profile. It does not launch a multi-broker cluster.

## Troubleshooting

- Port 8080 in use: stop the conflicting service or change the host mapping and `APP_ORIGIN` together; CSRF origin mismatch must not be bypassed.
- Health 503: inspect migration completion and database logs; do not start commands against the wrong schema version.
- Empty analytics: start the worker and inspect actual run/quarantine codes.
- Reused key with changed payload: resend original details or review the original result before expressing a new instruction.
- Future database version or checksum error: use the matching source; never edit the recorded applied migration.

[Shutdown and restore](OPERATIONS_RUNBOOK.md). No Docker runtime exists in the assistant's editing workspace; container execution evidence comes from the linked GitHub Actions runner, not an invented local session.

## Upgrading to Subhanjan and isolated visitors

Rebuild/restart with `docker compose up --build -d --wait --wait-timeout 180`. The migration service applies 006–008; it does not require deleting the volume. Migration 006 changes the old Alex Morgan display name to Subhanjan Das without changing internal IDs or ledger history. The UI uses the `subhanjan` local persona alias; the old `alex` alias remains compatible with existing scripts. Do not manually rewrite foreign keys to rename a customer.

[Visitor provisioning](VISITOR_SCENARIOS.md) is an additional operator command for separately configured OIDC identities. It does not require nor create a paid provider during local startup.
