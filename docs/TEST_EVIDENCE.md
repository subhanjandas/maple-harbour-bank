# Acceptance evidence

Initial local result: TypeScript compilation and production build passed. Python modules compile. PostgreSQL-dependent tests are skipped without `TEST_DATABASE_URL`; those skips are not passes.

GitHub Actions runs the banking suite against real PostgreSQL using separate API and worker login roles, then Playwright against the actual API/worker, followed by container build/startup/health checks. Successful runs preserve raw JUnit, browser results, actual screenshots and tested commit identity in `evidence/` and `docs/assets/`.

Pending execution: banking concurrency, real process exits, role denial, end-to-end browser journey and Compose startup. The next revision of this file must link the actual run and report counts, failures and resource limits honestly.
