# Project state · release 0.2

## Reproducible identity

- Repository: https://github.com/subhanjandas/maple-harbour-bank
- Release 0.2 merged into `main` in [PR #2](https://github.com/subhanjandas/maple-harbour-bank/pull/2), merge commit **`4b02c998731fb91a56a31dfd0a69f0866d371481`**. Implementation branch: `feat/customer-onboarding`, based on `dcdd2ea6c0a1f1e848e002be1137a12a47a339dd`. Release 0.1 remains in [PR #1](https://github.com/subhanjandas/maple-harbour-bank/pull/1).
- Atlas import/inspection: **`69586431f1ed0ed5bf3c7d698b246b0662542d6d`**, application 1.2.0/model 0.5.0, MIT. Atlas and other repositories were not modified.
- Latest fully tested application source: **`4d50366f09658992b6fed373e7269e76ebb6b892`**, [successful run 39071620676](https://github.com/subhanjandas/maple-harbour-bank/actions/runs/39071620676): **49 backend tests, two browser tests**, build, audits, actual container HTTP journey, restore and measured workloads.
- Release 0.2 evidence/capture checkpoint: **`f066ed8a49b14b3ee63c1e13245c591d2086ec56`**. [PR #2](https://github.com/subhanjandas/maple-harbour-bank/pull/2) contains the visitor/name increment. The final manifest and UI release metadata were included in the passing run. Later handoff commits change documentation only.
- `evidence/ci-summary.json` records the latest **successful tested source commit** and capture provenance; `git rev-parse HEAD` records the current checkout. Evidence commits follow tested code commits, avoiding a self-referencing commit hash.

## Running and hosted URLs

| Address | Status |
|---|---|
| `http://localhost:8080` | Local core after documented Compose startup; not a public deployed URL |
| `http://localhost:8080/api/health/ready` | Local database/migration readiness |
| https://subhanjandas.github.io/banking-model-atlas/ | Existing independent Model Atlas |
| https://subhanjandas.github.io/banking-model-atlas/?page=engineering | Existing static engineering reference; distinct from live app control room |
| Persistent hosted banking application | **Not deployed; no paid resources created** |

The editing workspace has no Docker/unprivileged PostgreSQL runtime. Actual server, browser and Compose execution occurs on the GitHub Actions runner. Ephemeral CI deployments are stopped; they are not a persistent demo.

## What is implemented

Core services: React/TypeScript/nginx, FastAPI modular backend, PostgreSQL and separately runnable durable worker. Forward migrations 001–008, checksum gate, deterministic synthetic funding, separate schema/API/worker credentials and health checks.

Payment depth: owned CAD accounts, booked/available convention, idempotent command responses, locked funds, immutable balanced postings with account roll-forward checks, internal transfer/reversal, outbound posting, simulator settlement, partial returns and report-date correction. Role/scope/tenant enforcement, opaque revocable sessions, CSRF and OIDC code/PKCE relying-party tests.

Data depth: source snapshots committed atomically with banking records; original-envelope archive before acknowledgement; versioned history/current projections; source-controlled versioned daily publication; rejected attempts/quarantine; actual payment→journal→event→archive→run→publication trace. Initial analytical storage is a PostgreSQL prototype, **not Delta Lake**.

Experience: customer accounts/payments, operations lifecycle/returns, approved analytics and actual engineering control room; light/Dusk; manifest-backed architecture with search, path/planned filters, zoom/pan, node/edge contracts, guided illustrative mode, actual-evidence guidance and accessible table alternative; permanent/contextual Atlas links and author credit.

## Capability matrix

| Capability | Status | Exact coverage / next gap |
|---|---|---|
| Customer/party and onboarding | Implemented and tested | Synthetic principals seeded; operator-provisioned OIDC visitors implemented and tested; real identity verification not implemented |
| Products and pricing | Modeled only | Atlas reference; no operational pricing catalog |
| Deposit accounts | Implemented and tested | Owned seeded CAD deposits, booked/available; hold workflow and joint holders planned |
| Payments and beneficiaries | Implemented and tested | Seeded beneficiary, own-account transfer, outbound command and lifecycle; beneficiary management planned |
| Cards, authorization and clearing | Modeled only | Atlas reference; card integration simulator planned |
| Ledger and reconciliation | Implemented and tested | Immutable balanced journals and deposit roll-forward; dedicated analytical reconciliation fact planned |
| Settlement acknowledgements and returns | Simulated integration | Scoped employee commands, installments and attribution corrections; no actual rails |
| Loans and repayments | Modeled only | Atlas reference; operational loan allocation/arrears planned |
| Business organizations and approvals | Simulated integration | Browser profile implements organization-scoped maker/checker, holds, approval/rejection; server implementation planned |
| Fraud and disputes | Modeled only | Atlas reference; operations simulation/detection planned |
| Collections | Modeled only | Atlas reference; no operational collections engine |
| Customer service | Modeled only | Atlas reference; case handling planned |
| Fees, interest and statements | Modeled only | Atlas reference; no accrual/statement generation |
| Reference data and FX | Implemented and tested | Actual BoC reference CLI/cache and recorded fixture; executable FX quotes/cross-border planned |
| Identity and access | Implemented and tested | Trusted sessions, backend authorization, signed test-provider OIDC; isolated visitor provisioning implemented and tested; deployed provider pending |
| Data platform operations | Implemented and tested | Polling/archive/projection/publication prototype, process recovery; full distributed lakehouse pending |
| Real customers, actual money movement, licensed bank/regulatory certification | Out of scope | Never claimed |

## First end-to-end acceptance coverage

| Gate | Current coverage |
|---|---|
| Authenticate and show owned accounts | Local persona simulator + server session; signed OIDC code-flow tests; deployed IdP pending |
| Validate funds/authorization/transitions/idempotency | Implemented; concurrent and negative tests |
| Atomic banking + balanced ledger + outbox | Implemented; database constraints and same-transaction writes |
| Employee lifecycle and partial returns | Implemented via clearly labelled simulator commands |
| Analytical layers and reconciled freshness | PostgreSQL prototype; approved publication API |
| Late correction of analytical period | Tested reporting-date revision; cash remains unchanged |
| Duplicate effects and worker interruption | Real duplicate/concurrency tests and two child-process exit windows |
| Missing-source prevents bad publication | Tested rejection and last-good preservation |
| Explorer and Atlas context | Implemented manifest/contract inspection and verified entity IDs |

External batch controls, CDC/broker/node failure, Spark checkpoint semantics, controlled poison-record disposition and published lakehouse tables remain later gates. No universal exactly-once or HA claim is made.

## Resume commands

```bash
python3 scripts/bootstrap.py
docker compose up --build -d --wait --wait-timeout 180
curl --fail http://localhost:8080/api/health/ready
# Optional actual HTTP demo with installed Python dependencies:
uv run --project backend python scripts/demo_journey.py
# Safe independent restore drill:
bash scripts/backup_restore.sh
# Stop processes, preserve durable volume:
docker compose down
```

Migration order: `001_core.sql`, `002_journal_trigger.sql`, `003_scenario_bounds.sql`, `004_managed_owner.sql`, `005_outbox_access.sql`, `006_customer_name.sql`, `007_visitor_scenarios.sql`, `008_serving_isolation.sql`. Existing applied checksums must not be edited. Synthetic seed reruns do not re-fund accounts. [Full setup](LOCAL_SETUP.md).

## Next acceptance gate

1. Release 0.2 adds Subhanjan, isolated visitor provisioning and analytical RLS; all 49 backend checks, two browser journeys, audits, container and restore acceptance passed. Read `evidence/ci-summary.json`, the linked run, actual screenshots/demo and known limitations before extending the source.
2. Public release: verify the new isolated visitor provisioning against a real deployed OIDC provider, validate hosted permissions/restore/TLS/secrets, select the persistent topology within a user-provided monthly spending ceiling. Render was found as a deployment integration but is not connected or provisioned.
3. Streaming/lakehouse release: compatibility-pin Debezium/Kafka/Spark/Delta/storage/Airflow in manageable groups; preserve the v1 contract and one-publisher cutover; add independent batch manifests, replay/disposition and distributed failure evidence.
4. Expand into business approvals or loans only after the connected slice and its performance/recovery claims remain demonstrable.

Known first-profile limits: full-history analytical rebuilds; a tenant quota counter serializes source admission; one database failure domain; scale-lab override supplied but not yet executed as a separate Compose project; local persona simulation; no business maker/checker; no cloud production OIDC; no time-based off-host raw purge; no distributed telemetry backend or multi-node HA.

## Current increment · 18 October 2026

Branch `feat/customer-onboarding` starts at `dcdd2ea6c0a1f1e848e002be1137a12a47a339dd`. Customer display name is Subhanjan Das; legacy `harbour:alex` stays a stable internal identity. Migration 006 changes only the old seeded display names. New operator-only `python -m mhb.provision` creates bounded, expiring, customer-only scenarios. Repeating identity admission cannot refund, reset or reactivate. Analytical serving and metadata lineage now fail closed without a trusted tenant. See [visitor operations](VISITOR_SCENARIOS.md). No paid resources, new public URL or real identity provider has been created.

## Release 0.3 in progress · public Pages profile

User constraint: **CAD 0, no paid hosting**. Branch `feat/public-pages` adds a publicly deployable profile using the existing React shell, browser Web Worker and IndexedDB. Customer payments/returns, business maker/checker holds, analytics and actual recovery experiments execute on each visitor’s device. This profile has simulated roles, not server authentication; PostgreSQL/OIDC tests remain independently valid for the server lab.

New entry points: `web/src/simulation/`, `web/src/Business.tsx`, `web/src/RecoveryLab.tsx`, `architecture/public-manifest.json`, `.github/workflows/pages.yml`. Read [PUBLIC_DEMO](PUBLIC_DEMO.md) before extending. Build: `VITE_PUBLIC_DEMO=true VITE_BASE_PATH=/maple-harbour-bank/ npm run build --prefix web`. Browser acceptance: `cd web && npx playwright test -c playwright.pages.config.ts`. Acceptance and first Pages deployment pending. Repository administrator must have Pages configured for GitHub Actions; no account token is bundled.
