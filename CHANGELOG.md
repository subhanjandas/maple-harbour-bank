# Changelog

## 0.1.0 · 17 October 2026 · first payment slice

- Inspect/pin Atlas application 1.2.0/model 0.5.0 at `69586431f1ed0ed5bf3c7d698b246b0662542d6d`; preserve MIT provenance and selected mappings.
- Add FastAPI/PostgreSQL core, checksum-verified forward migrations, separate service logins, synthetic funding and local Compose startup.
- Add sessions, OIDC authorization-code/PKCE relying party, backend ownership/team/tenant enforcement, CSRF and request limits.
- Add exact CAD outbound/internal payment posting, immutable balanced journals, idempotency, settlement simulation, partial returns, internal reversals and reporting-date corrections.
- Add durable polling outbox archive, versioned Silver history/projection, source-controlled Gold publication, quarantine codes and actual lineage.
- Build light/Dusk React customer, operations, analytics and engineering workspaces; interactive architecture from a shared manifest; permanent Atlas links and author credit.
- Add real PostgreSQL concurrency/access/crash tests, signed test-provider OIDC tests, Playwright acceptance/captures, dependency/source guards, logical restore drill and separately measured source-record/command workloads.
- Correct trigger record-field resolution in migration 002; add bounded synthetic sources in 003; make trusted-owner RLS behavior explicit for managed PostgreSQL in 004.

Not yet a persistent public deployment, a Delta lakehouse, a multi-node resilience claim or a complete bank. Capability and acceptance status live in `docs/PROJECT_STATE.md`.
- Restrict source outbox reads to tenant-scoped metadata for API credentials; keep original envelopes accessible only to the processing role.
