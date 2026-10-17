# Operations runbook

Start with `docker compose ps`, `/api/health/ready`, worker logs and an engineer's `/api/engineering` view. Never repair a financial history by updating posted lines or disabling constraints.

## Basic operations

```bash
# Repository root, local development only
python3 scripts/bootstrap.py
docker compose up --build -d
docker compose logs --tail=100 api worker
curl --fail http://localhost:8080/api/health/ready
# Actual HTTP journey (use the installed Python dependency environment):
backend/.venv/bin/python scripts/demo_journey.py
# Seed safely without re-funding existing accounts:
docker compose run --rm migrate
# Worker process recovery:
docker compose restart worker
# One worker batch, using its restricted credential:
docker compose exec worker python -m mhb.pipeline --once
# Rebuild request, at most 31 requested business dates:
docker compose exec worker python -m mhb.pipeline --backfill harbour 2026-10-01 2026-10-17
```

The current rebuild replays all current source history. The date argument bounds the request, not work volume. It is not an incremental partition optimization. These operator controls are intentionally absent from public browser endpoints.

## Investigate and recover

| Symptom | Expected invariant | Recovery |
|---|---|---|
| Client loses response | Committed instruction remains single | Retry the original body and original idempotency key; inspect payment before a new intent |
| API process dies before commit | No partial account/journal/event effects | Restart API; retry original key |
| Worker dies after archive write, before ack | One immutable archive identity; pending source redelivered | Restart worker; checksum match deduplicates; inspect attempts and acknowledgement |
| Worker dies during publication | Last committed pointer unchanged | Restart; transaction rolls back; retry source-complete snapshot |
| Missing source / incomplete archive | Last good publication survives | Drain backlog and compare source identities/checksum; do not lower source expectations |
| Contract poison record | Preserved original source plus quarantine code; no bad publication | Stop blind retry, investigate producer/contract. Reviewed disposition tooling remains a next gate; do not mutate Bronze |
| Old reporting date corrected | Booked cash unchanged; historical attribution republishes | Correct the return reporting date with a new command key; inspect old/new periods and aggregate version |
| Source grows to scenario limit | Entire new command rolls back; accepted money never loses an event | Archive/restore evidence and start a fresh isolated scenario, or approve a higher measured lab quota |
| Data appears stale | UI exposes age and unpublished events | Check worker, queue and latest successful run; a view refresh is not a pipeline refresh |
| Unknown migration version/checksum | Startup fails closed | Use matching application or reviewed forward migration; never edit an applied checksum |

## Recorded failure experiments

The pytest report contains real tests of: 40 concurrent identical commands; 30 concurrent hot-account attempts; invalid transition and excess return; cross-customer/tenant/team denial; raw database-role denial; process exit 17 after committed archive/before acknowledgement; process exit 19 inside publication; and missing-source rejection followed by successful repair. Read [test evidence](TEST_EVIDENCE.md) for exact tested commit and run. These are process and data-boundary experiments on one PostgreSQL host, not broker/node-failure tests.

## Backup and restore

`bash scripts/backup_restore.sh` uses `pg_dump -Fc`, restores into a separate `mhb_restore_check` database, compares journal-line counts and reruns journal balance/account roll-forward checks. It never restores over live `mhb`. CI runs the drill after an actual HTTP payment/settlement/return journey, so operational postings and archived/published evidence are present. The temporary restored database is dropped; the local backup remains in ignored `.runtime/backups/`.

This is a logical database restore drill on one host. It does not benchmark cloud disaster recovery, WAL/PITR, off-host durability, production RPO or RTO. A hosted profile requires encrypted off-host backups, credential restoration and a timed recovery exercise.

## Retention and bounded resource controls

Development scenarios are limited to 50,000 source events by a database trigger; a single envelope is at most 64 KiB and a payment at most 100 return installments. The counter is updated atomically with the source event, so exhaustion rolls back the command. It adds a tenant-level serialization point; the performance report must disclose this trade-off. A scale-lab operator can review a larger limit up to 1M events with measured storage, rather than silently dropping evidence.

No automatic source/ledger deletion is allowed in this release. The record quota bounds scenario growth; time-based off-host archive/purge remains a hosted release requirement. Never independently truncate outbox/Bronze/Silver because source completeness and referential history depend on them. Keep local backups for a documented experiment, encrypt if leaving the machine, and explicitly remove expired copies after verifying retained recovery evidence. Sessions expire at 30 minutes; deleting expired sessions/rate-window rows is restricted operator maintenance until a tested retention job is introduced.

CI artifacts expire after 14 days. Committed evidence consists of synthetic screenshots, aggregate benchmarks and test results. Public hosting must additionally cap active scenarios, storage, backup retention and egress.

## Shutdown

`docker compose stop` stops processes and preserves the named volume. `docker compose down` removes containers/network and preserves the database volume. Removing volumes destroys the local synthetic database; take/verify a backup first and do not automate that destructive action for a public user.

## Future CDC runbook requirements

Before enabling Debezium: record slot/publication ownership, supported PostgreSQL/connector versions, snapshot/cutover cutoff and one active publisher. Monitor source lag, `confirmed_flush_lsn`, `restart_lsn`, retained WAL bytes and disk headroom. Test source restart, connector outage, slot recovery and poison records. A single Kafka broker is not HA; node/broker-failure tests need the exact tested multi-node topology.

## Invited synthetic visitors

Use the [visitor scenario runbook](VISITOR_SCENARIOS.md) with a protected operator connection. Repeated admission never refunds or reactivates. If capacity is exhausted, stop admission and review retained scenarios/storage; do not delete immutable ledger rows or lift limits blindly. Deactivation preserves financial/source evidence and blocks subsequent authentication. There is no automatic purge or reactivation job.
