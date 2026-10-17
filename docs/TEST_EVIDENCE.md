# Acceptance evidence

## Verified release checkpoint

[Successful run 39045330756](https://github.com/subhanjandas/maple-harbour-bank/actions/runs/39045330756) tested source **`f7330756424c89f210cc98db08f6ba4490fb6ed5`**:

- **42 backend tests**, zero skips, failures or errors (11.396 seconds). Real PostgreSQL, actual separate service logins, ordinary non-superuser migration owner, signed test-provider code/PKCE validation and recorded-source cache tests.
- **Two real Playwright browser tests**, covering payment→settlement→return→publication→lineage, role workspaces, theme persistence, mobile overflow and architecture text access. Actual screenshots and a recorded WebM demonstration are preserved in `docs/assets/`.
- TypeScript production build; Python/npm dependency audits with zero known findings; tracked-source guard; documentation/Atlas-link checks.
- Deterministic 100K/1M analytical-record query measurements and 300 distinct accepted HTTP payment commands, zero errors; exact workload/tails in `PERFORMANCE.md` and raw report.
- Core Docker images built, migrated, seeded and started. An actual HTTP payment, duplicate request, settlement, partial return and worker publication ran through the container reverse proxy. Its trace is `evidence/core-journey.json`.
- Logical backup restored into a different database after that journey, compared ledger counts and reran journal/account invariants. `evidence/restore-drill.txt` records the result; no restore over the live database occurred.

`evidence/ci-summary.json` records the exact successful tested source; raw JUnit, browser JSON, capture provenance, benchmark and Compose evidence are committed by the successful workflow. Evidence is not hand-authored as a pass. Later documentation-only handoff commits do not change the application code tested above.

The editing workspace's TypeScript build, Python compilation and two reference-cache tests pass. Local PostgreSQL tests skip without a supplied server; skipped tests are explicitly **not** acceptance passes. The GitHub runner supplies real PostgreSQL 18.6 and actual separate API/worker login roles.

## Experiment matrix

| Boundary / experiment | Expected invariant | Injected condition | Verified baseline observation | Recovery |
|---|---|---|---|---|
| Concurrent duplicate API intent | One payment, original response | 40 calls, same key/body | One identity/effect, three source events | Replay original key |
| Hot-account overspend | Nonnegative availability, exact roll-forward | 30 concurrent CAD 300 requests against CAD 5,000 | 16 accepted; CAD 200 remains | Reject remaining requests without partial effects |
| Return lifecycle | Positive total ≤ original; separate settlement | Early/excess/duplicate/final installments | Early/excess rejected; duplicate stable; full return terminal | Correct intent, reuse proper key |
| Ledger mutation | Original records unchanged; balance checked | UPDATE, DELETE, extra lines on closed journal, unbalanced journal, wrong booked balance | Database errors; invalid transactions roll back | New compensating journal |
| Archive/ack crash | One archive identity and unacknowledged source | Child exits 17 after sink commit, before ack | One preserved Bronze row, zero ack before retry; three rows after retry, attempts show redelivery | Restart worker |
| Publication crash | Last successful pointer unchanged | Child exits 19 inside publication | Old pointer survives; subsequent rebuild succeeds | Replay source-complete snapshot |
| Missing source | No incomplete analytical publication | Archive only part of a new source set | Rejected run/code and unchanged old publication | Drain archive, retry |
| Older delivery / replay | No current-state downgrade | Archive versions in reverse order then replay | Highest version remains, unique event counts preserved | Normal worker retry |
| Late reporting attribution | Historical period changes, booked cash does not | Later revision changes installment reporting date | New period totals, same deposit cash and journals | Publish next source version |
| Customer/team/tenant authorization | No cross-boundary resource access | Other customer, Vancouver operator, other tenant | Denied/404; own lists remain scoped | Correct principal/scope |
| Raw/service separation | API/worker have different grants | Actual service logins query forbidden tables | PostgreSQL permission errors | Use authorized serving or operator path |
| Session/CSRF/OIDC | Trusted identity, rejected forged/expired sessions | Wrong origin/CSRF, expired/revoked session, wrong state/issuer/audience/nonce/signature/expiry | Requests denied; valid PKCE flow maps only provisioned subject | New trusted login |
| BoC outage | Never invent a rate or overwrite good cache | 503 × three with/without cache | Explicit stale provenance or unavailable; cache bytes unchanged | Retry bounded source fetch later |

Additional verified checks cover ordinary-owner migration/outer-commit constraints, scenario-quota rollback, tenant-scoped outbox metadata with raw-column denial and payment/return restore. The ordinary-owner check runs without superuser privileges. Business organization approvals remain unimplemented; synthetic tenant tests must not be counted as maker/checker coverage.

## Limits

All process failures use one database host. No Kafka broker/node-failure experiment, multi-region failover, production identity-provider deployment, payment-rail integration, regulatory certification or universal exactly-once behavior was tested. Query microbenchmarks are not million-transaction banking tests. The dependency audits report known advisories at execution time, not absence of all vulnerabilities.

The first failed [run 39043250941](https://github.com/subhanjandas/maple-harbour-bank/actions/runs/39043250941) exposed a trigger record-shape bug; migration 002 fixed it. A later managed-owner test initially expected a deferred constraint to fire at an inner savepoint; it was corrected to exercise the outer commit. Failed run history remains available rather than being relabelled as successful evidence.
