# Project state · release 0.1 implementation checkpoint

Source checkout: `feat/release-0-payment-core`. Base: `81498870632b53d3e20ba9195830035f3d9c1941`.
Atlas inspected/imported: `69586431f1ed0ed5bf3c7d698b246b0662542d6d` (MIT).

Use `git rev-parse HEAD` for this document's current checkout identity. An exact tested source commit is recorded independently in `evidence/ci-summary.json` after the acceptance workflow succeeds; screenshot provenance records that same source commit. This avoids a self-referencing commit hash in its own contents.

Implemented source: migrations, seed, API, database service roles, opaque sessions with ownership/scope checks, OIDC code flow, CAD posting, partial returns, internal transfer/reversal, transactional outbox, durable worker, analytical publication prototype, React workspaces and manifest-backed architecture explorer.

Local validation: TypeScript production build passed. The workspace has no Docker and cannot create an unprivileged PostgreSQL process. Integration, browser and Compose execution are assigned to GitHub Actions and remain unverified until the linked run completes. Do not treat skipped local database tests as passes.

No hosted banking URL exists. No paid infrastructure has been created. Atlas remains unchanged and independently deployed. Full lakehouse, organization approvals, production OIDC provider integration and public visitor isolation remain release gates.

## Resume

1. Inspect the branch, `evidence/ci-summary.json`, workflow results and test evidence.
2. `python scripts/bootstrap.py`; `docker compose up --build -d`.
3. Open `http://localhost:8080`; health `http://localhost:8080/api/health/ready`.
4. Migration: `001_core.sql`, checksum checked before startup. Synthetic seed is idempotent.
5. Run the first payment acceptance journey. Repair any failed tests before expanding scope.
6. Next gate: confirm production OIDC through a real provider, public scenario isolation, backup/restore and measured workload, then select hosting within the user's spending ceiling.

The analytical layers currently run inside PostgreSQL. They are not a deployed Delta lakehouse or highly available cluster.
