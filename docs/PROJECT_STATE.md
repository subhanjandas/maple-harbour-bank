# Project state · release 0.1

## Reproducible identity

- Repository: https://github.com/subhanjandas/maple-harbour-bank
- Implementation branch: `feat/release-0-payment-core`; initial base `81498870632b53d3e20ba9195830035f3d9c1941`.
- Atlas import/inspection: **`69586431f1ed0ed5bf3c7d698b246b0662542d6d`**, application 1.2.0/model 0.5.0, MIT. Atlas and other repositories were not modified.
- Latest fully tested application source: **`f7330756424c89f210cc98db08f6ba4490fb6ed5`**, [successful run 39045330756](https://github.com/subhanjandas/maple-harbour-bank/actions/runs/39045330756): **42 backend tests, two browser tests**, build, audits, actual container HTTP journey, restore and measured workloads.
- Evidence/capture checkpoint: **`c0fd0922`** (resolve the full identity with `git log` or `evidence/ci-summary.json`'s tested parent). Final handoff changes are documentation only; verify `git diff f733075 -- backend db web architecture scripts compose.yaml infra .github` before assuming a later code change was tested.
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

Core services: React/TypeScript/nginx, FastAPI modular backend, PostgreSQL and separately runnable durable worker. Forward migrations 001–005, checksum gate, deterministic synthetic funding, separate schema/API/worker credentials and health checks.

Payment depth: owned CAD accounts, booked/available convention, idempotent command responses, locked funds, immutable balanced postings with account roll-forward checks, internal transfer/reversal, outbound posting, simulator settlement, partial returns and report-date correction. Role/scope/tenant enforcement, opaque revocable sessions, CSRF and OIDC code/PKCE relying-party tests.

Data depth: source snapshots committed atomically with banking records; original-envelope archive before acknowledgement; versioned history/current projections; source-controlled versioned daily publication; rejected attempts/quarantine; actual payment→journal→event→archive→run→publication trace. Initial analytical storage is a PostgreSQL prototype, **not Delta Lake**.

Experience: customer accounts/payments, operations lifecycle/returns, approved analytics and actual engineering control room; light/Dusk; manifest-backed architecture with search, path/planned filters, zoom/pan, node/edge contracts, guided illustrative mode, actual-evidence guidance and accessible table alternative; permanent/contextual Atlas links and author credit.

## Capability matrix

| Capability | Status | Exact coverage / next gap |
|---|---|---|
| Customer/party and onboarding | Modeled only | Synthetic principals seeded; interactive onboarding/identity verification not implemented |
| Products and pricing | Modeled only | Atlas reference; no operational pricing catalog |
| Deposit accounts | Implemented and tested | Owned seeded CAD deposits, booked/available; hold workflow and joint holders planned |
| Payments and beneficiaries | Implemented and tested | Seeded beneficiary, own-account transfer, outbound command and lifecycle; beneficiary management planned |
| Cards, authorization and clearing | Modeled only | Atlas reference; card integration simulator planned |
| Ledger and reconciliation | Implemented and tested | Immutable balanced journals and deposit roll-forward; dedicated analytical reconciliation fact planned |
| Settlement acknowledgements and returns | Simulated integration | Scoped employee commands, installments and attribution corrections; no actual rails |
| Loans and repayments | Modeled only | Atlas reference; operational loan allocation/arrears planned |
| Business organizations and approvals | Planned | Organization membership, maker/checker and approval workflow not implemented |
| Fraud and disputes | Modeled only | Atlas reference; operations simulation/detection planned |
| Collections | Modeled only | Atlas reference; no operational collections engine |
| Customer service | Modeled only | Atlas reference; case handling planned |
| Fees, interest and statements | Modeled only | Atlas reference; no accrual/statement generation |
| Reference data and FX | Implemented and tested | Actual BoC reference CLI/cache and recorded fixture; executable FX quotes/cross-border planned |
| Identity and access | Implemented and tested | Trusted sessions, backend authorization, signed test-provider OIDC; deployed provider and visitor provisioning pending |
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

Migration order: `001_core.sql`, `002_journal_trigger.sql`, `003_scenario_bounds.sql`, `004_managed_owner.sql`, `005_outbox_access.sql`. Existing applied checksums must not be edited. Synthetic seed reruns do not re-fund accounts. [Full setup](LOCAL_SETUP.md).

## Next acceptance gate

1. Current release acceptance is complete. Read `evidence/ci-summary.json`, the linked run, actual screenshots/demo and known limitations before extending the source.
2. Public release: provision isolated synthetic visitor scenarios and a real OIDC provider, validate hosted permissions/restore/TLS/secrets, select the persistent topology within a user-provided monthly spending ceiling. Render was found as a deployment integration but is not connected or provisioned.
3. Streaming/lakehouse release: compatibility-pin Debezium/Kafka/Spark/Delta/storage/Airflow in manageable groups; preserve the v1 contract and one-publisher cutover; add independent batch manifests, replay/disposition and distributed failure evidence.
4. Expand into business approvals or loans only after the connected slice and its performance/recovery claims remain demonstrable.

Known first-profile limits: full-history analytical rebuilds; a tenant quota counter serializes source admission; one database failure domain; local persona simulation; no business maker/checker; no cloud production OIDC; no time-based off-host raw purge; no distributed telemetry backend or multi-node HA.
