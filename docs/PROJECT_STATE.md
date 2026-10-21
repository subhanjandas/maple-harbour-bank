# Project state · release 0.4 candidate; release 0.3 publicly deployed

## Current implementation checkpoint

Branch `feat/live-observatory`, based on exact main `0004655db84e67cd5426a80cba40be15167e13e6`. Release 0.4 adds the [live observatory](LIVE_OBSERVATORY.md), seeded durable synthetic activity and selected-payment actual lineage. Local TypeScript/production builds pass; new acceptance and deployment are pending CI. No database migration or dependency change. Browser schema 1 is extended additively; existing records and posted history remain intact.

Next gate: run all public/server acceptance, preserve actual captures, merge and verify Pages. The release 0.3 deployment identity below remains authoritative until then.

## Reproducible identity

- Repository: https://github.com/subhanjandas/maple-harbour-bank
- Live app: **https://subhanjandas.github.io/maple-harbour-bank/**
- Release merged in [PR #3](https://github.com/subhanjandas/maple-harbour-bank/pull/3), deployed source **`8ee3566baebbcf89c7e3677c6fd93803ae422441`**.
- [Successful Pages deployment 39090991069](https://github.com/subhanjandas/maple-harbour-bank/actions/runs/39090991069); [successful server acceptance on main 39090991147](https://github.com/subhanjandas/maple-harbour-bank/actions/runs/39090991147).
- Preserved raw evidence tests implementation **`37fa7a9f02593655d4dff95ba4d9a646520e6697`**; actual public captures at `08c166e3fd955406578e2aa3c5e9e23dbfc2cbc8`, server captures at `0ccfd106e29938ede62373c1b4a6de1a9f3bdd48`. Differences to the deployed merge are evidence only. Later documentation commits do not change the deployed code.
- Atlas import/inspection: **`69586431f1ed0ed5bf3c7d698b246b0662542d6d`**, application 1.2.0/model 0.5.0, MIT. Atlas and other repositories were not modified.
- Budget is **CAD 0**. No paid hosting or additional cloud account was created. Standard public-repository GitHub runners, Pages and bounded one-day workflow artifacts are used.

## Running profiles and URLs

| Address / runtime | Verified status |
|---|---|
| https://subhanjandas.github.io/maple-harbour-bank/ | Public HTTPS app, HTTP 200, real browser payment/return/publication/recovery smoke passed |
| Public banking state | IndexedDB on each visitor’s device; worker processes while a page is open; reload resumes persisted state |
| `http://localhost:8080` | Separately runnable FastAPI/PostgreSQL core through Compose; ephemeral CI execution verified |
| `http://localhost:8080/api/health/ready` | Server database/migration readiness |
| https://subhanjandas.github.io/banking-model-atlas/ | Existing independent Model Atlas |
| https://subhanjandas.github.io/banking-model-atlas/?page=engineering | Existing static engineering reference, distinct from the app’s actual runtime control room |

The public role selector demonstrates workflows; it is not server authentication. Visitors control their own browser and storage. The server lab independently implements OIDC relying-party validation, sessions, service roles, RLS and financial concurrency. There is no shared publicly hosted PostgreSQL/IdP service. [Exact profile comparison](PUBLIC_DEMO.md).

## What works and what was tested

**Public profile:** Subhanjan’s owned CAD accounts, exact-cent outbound payments and internal transfers, immutable-through-command-interface journals, transactional source events, stable idempotency, simulated settlement, partial returns and analytical date corrections. Business maker/checker reserves funds before a separate approval, rejects self-approval and other organizations, then posts or releases the hold. A Web Worker archives original SHA-256 envelopes, verifies version/source/current-state controls and publishes reconciled daily activity. The control room exposes actual runs and isolated recovery controls. The architecture explorer labels public versus server topology and links to Atlas.

**Six public-browser tests passed** with zero skips/flakes: persistence and live lineage; duplicate/hot-account and ownership attacks; maker/checker and organization isolation; archive interruption and missing-source recovery; partial returns and late correction without extra cash; independent browsers and mobile Dusk topology. The browser test run took 12.368 seconds on the recorded implementation. Genuine captures are `docs/assets/public-*.png`.

**49 backend tests and two server-browser journeys passed**, with audits, actual Compose startup/payment/return/publication and independent backup restore. PostgreSQL migrations 001–008, trusted sessions/CSRF, scoped ownership/roles, service grants, immutable balanced journal constraints, concurrency, two signed OIDC visitors and subprocess crash boundaries remain covered. Data layers here are a PostgreSQL prototype, not Delta Lake.

**Deployed smoke:** a CAD 125 instruction, settlement and CAD 30 return produced five source events and reconciled publication. Withholding one input rejected refresh; replay recovered without duplicate financial effects. The exported evidence was independently checked for event SHA-256, balanced journals, source counts and totals. See `evidence/live-pages-smoke.json`, `evidence/live-pages-verification.json` and `docs/assets/public-live.jpg`.

## Capability matrix

| Capability | Status | Exact coverage / next gap |
|---|---|---|
| Customer/party and onboarding | Implemented and tested | Synthetic principals seeded; operator-provisioned OIDC visitors implemented and tested; real identity verification not implemented |
| Products and pricing | Modeled only | Atlas reference; no operational pricing catalog |
| Deposit accounts | Implemented and tested | Owned seeded CAD deposits, booked/available; browser business approval holds implemented; general holds and joint holders planned |
| Payments and beneficiaries | Implemented and tested | Seeded beneficiary, own-account transfer, outbound command and lifecycle; beneficiary management planned |
| Cards, authorization and clearing | Modeled only | Atlas reference; card integration simulator planned |
| Ledger and reconciliation | Implemented and tested | Immutable balanced journals and deposit roll-forward; dedicated analytical reconciliation fact planned |
| Settlement acknowledgements and returns | Simulated integration | Scoped employee commands, installments and attribution corrections; no actual rails |
| Loans and repayments | Modeled only | Atlas reference; operational loan allocation/arrears planned |
| Business organizations and approvals | Simulated integration | Public profile: tested maker/checker and organization separation, reserved funds, approval/rejection; server implementation planned |
| Fraud and disputes | Modeled only | Atlas reference; operations simulation/detection planned |
| Collections | Modeled only | Atlas reference; no operational collections engine |
| Customer service | Modeled only | Atlas reference; case handling planned |
| Fees, interest and statements | Modeled only | Atlas reference; no accrual/statement generation |
| Reference data and FX | Implemented and tested | Actual BoC reference CLI/cache and recorded fixture; executable FX quotes/cross-border planned |
| Identity and access | Implemented and tested | Trusted sessions, backend authorization, signed test-provider OIDC; isolated visitor provisioning implemented and tested; deployed provider pending |
| Data platform operations | Implemented and tested | Polling/archive/projection/publication prototype, process recovery; full distributed lakehouse pending |
| Real customers, actual money movement, licensed bank/regulatory certification | Out of scope | Never claimed |


## First acceptance journey

The public app completes customer → payment → balanced postings/outbox → employee settlement/return → archive/projection/publication → analyst/control-room/lineage. It persists across reloads, deduplicates repeated commands and handles an interrupted archive boundary. Missing source prevents publication. Guided animation is labelled illustration; runtime evidence is read from actual stored scenario records. The server profile proves its separate database guarantees in CI. A licensed bank, regulatory certification and real rails are out of scope.

## Resume and operate

Public app requires only a modern browser. Start with Subhanjan, then Taylor, Jordan and Casey; business uses Avery (maker) and Morgan (checker). No payment credentials or account registration are required.

```bash
# Build the public artifact:
npm ci --prefix web
VITE_PUBLIC_DEMO=true VITE_BASE_PATH=/maple-harbour-bank/ npm run build --prefix web
# Public browser acceptance:
cd web
npx playwright test -c playwright.pages.config.ts
```

Server profile from the repository root:

```bash
python3 scripts/bootstrap.py
docker compose up --build -d --wait --wait-timeout 180
curl --fail http://localhost:8080/api/health/ready
bash scripts/backup_restore.sh
docker compose down
```

Migration order: `001_core.sql`, `002_journal_trigger.sql`, `003_scenario_bounds.sql`, `004_managed_owner.sql`, `005_outbox_access.sql`, `006_customer_name.sql`, `007_visitor_scenarios.sql`, `008_serving_isolation.sql`. Applied checksums cannot be edited. The internal `harbour:alex` ID remains stable while the visible customer is Subhanjan Das. Seed reruns never re-fund accounts.

## Next acceptance gates

1. Keep both public and server tests green and update deployment/source evidence for each increment. Public deployment is operational; no further hosting budget or sign-in step is required for the current release.
2. Add independently controlled batch manifests/files, changed-file identity detection and bounded replay/disposition. Keep browser event contracts explicitly distinct from authoritative core events.
3. Expand business approvals into the PostgreSQL core with maker/checker and organization authorization; do not count browser-role tests as backend security proof.
4. Introduce CDC/Kafka/Spark/Delta/Airflow only in bounded local/CI groups after current compatibility and resource evidence. No paid resource is authorized. Preserve one-publisher cutover and original server event identities.

Known limits: browser storage can be cleared/evicted and is controlled by its owner; no cross-device state or processing while all pages are closed; bounded whole-state replay; no full production browser authentication. Server uses a single database failure domain and full-history rebuilds; lab override is supplied but unmeasured separately; no hosted IdP, off-host timed raw purge, distributed tracing backend or multi-node HA. Cards, loans, fraud and statements are unimplemented, as the matrix states.
