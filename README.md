# Maple Harbour Bank

**A Canadian banking simulation whose engineering you can trace.**

Built by **Subhanjan Das** · React/TypeScript · FastAPI · PostgreSQL · synthetic identities and simulated money.

[Model Atlas ↗](https://subhanjandas.github.io/banking-model-atlas/) · [Engineering Reference ↗](https://subhanjandas.github.io/banking-model-atlas/?page=engineering) · [Current project state](docs/PROJECT_STATE.md)

The first working slice connects owned accounts, simulated payments, balanced immutable postings, settlement/partial returns, a durable outbox and reconciled analytical publications. The customer, employee, analyst and engineer workspaces use server-enforced permissions.

**Server release 0.2:** 49 backend tests + 2 browser tests passed, along with actual container startup, HTTP payment/return processing and backup/restore. [Exact evidence and tested commit →](docs/TEST_EVIDENCE.md)

![Actual customer workspace after posting a simulated payment](docs/assets/customer-overview.png)

[Recorded working demonstration (WebM)](docs/assets/payment-demo.webm) · [Light](docs/assets/customer-light.png) / [Dusk](docs/assets/customer-dusk.png) · [Operations](docs/assets/operations.png) · [Analytics](docs/assets/analytics.png) · [Architecture](docs/assets/architecture.png)

*Actual captures of the application against a real API, worker and PostgreSQL in the acceptance environment. [Capture provenance](docs/assets/provenance.json). No persistent public banking deployment exists yet. PostgreSQL analytical tables are the initial prototype; Kafka/Spark/Delta/Airflow remain planned.*

## Start the core

```bash
python3 scripts/bootstrap.py
docker compose up --build -d
curl --fail http://localhost:8080/api/health/ready
```

For the public zero-cost profile, see [Public demo](docs/PUBLIC_DEMO.md). The server lab is also runnable locally: open **http://localhost:8080**. Choose Subhanjan (customer), Taylor (operations), Jordan (analyst) or Casey (engineer). This selector is a loopback-only **development authentication simulator**; hosted mode disables it and requires OIDC.

1. Subhanjan posts a simulated CAD beneficiary payment; its available balance changes in the same transaction as the ledger and outbox.
2. Taylor acknowledges simulated settlement and records a partial return.
3. The worker archives original envelopes, validates source controls and publishes activity.
4. Jordan sees the publication, source cutoff and freshness. Casey sees actual backlog and run outcomes.
5. Open a payment trace to follow journal → event → archive receipt → ingestion run → publication.

No real customer data or payment rails. This is not a licensed bank, certified compliance implementation or complete production core.

## Two connected systems

```mermaid
flowchart TD
  Web["Role-aware web application"] --> API["Authorized banking API"]
  API --> Core["PostgreSQL accounts and immutable ledger"]
  Core --> Outbox["Transactional outbox"]
  Outbox --> Worker["Durable polling worker"]
  Worker --> Bronze["Bronze original envelopes"]
  Bronze --> Silver["Silver history and current projections"]
  Silver --> Gold["Gold versioned publication"]
  Gold --> Serving["Approved analytical serving API"]
  Serving --> Web
```

Spending always uses operational funds protected by database locks. Dashboards use a published analytical version and expose staleness. The architecture explorer and [generated topology](docs/ARCHITECTURE_GENERATED.md) share [one versioned manifest](architecture/manifest.json).

## Engineering claims and boundaries

| Claim | Implemented mechanism | Evidence gate |
|---|---|---|
| No overspending | Canonical account locks; booked minus held funds | Concurrent hot-account test |
| Duplicate command, stable response | Actor/tenant/key lock and stored response | Concurrent duplicate storm |
| Balanced immutable history | Deferred journal constraints, append-only triggers and closed journals | Direct database negative tests |
| Crash recovery | Archive commit before ack; idempotent event identity | Real child-process exits |
| Trustworthy publication | Source identity/checksum controls; atomic serving pointer | Missing-source rejection retains last good |
| No financial snapshot double-count | Versioned history plus latest aggregate projection | Partial returns and late attribution correction |
| Access boundaries | Opaque session, CSRF, scope/ownership and actual DB service roles | Cross-customer/tenant/scope and raw denial tests |

A single host is not high availability. At-least-once delivery is not universal exactly-once processing. See [test evidence](docs/TEST_EVIDENCE.md) for what actually ran.

The measured hot-account command baseline completed three 100-command repetitions at **50.02 / 115.25 / 105.86 accepted commands/s**, zero errors, on a 4-CPU/16GB CI runner. The p99 varied from 483 to 1,168ms. This is a short workload baseline, not maximum sustainable capacity. The separate million-record experiment measures analytical queries, not a million bank transactions. [Raw samples, plans and costs →](docs/PERFORMANCE.md)

## Explore the implementation

- [Architecture](docs/ARCHITECTURE.md) and [trade-offs](docs/DECISIONS.md)
- [Financial semantics](docs/DOMAIN_RULES.md), [contracts](docs/DATA_CONTRACTS.md) and [metrics](docs/METRICS.md)
- [Local setup](docs/LOCAL_SETUP.md), [recovery runbook](docs/OPERATIONS_RUNBOOK.md) and [security](docs/SECURITY_AND_ACCESS.md)
- [Deployment and cost](docs/DEPLOYMENT.md), [performance](docs/PERFORMANCE.md) and [source inventory](docs/SOURCE_CATALOG.md)
- [Interview walkthrough](docs/INTERVIEW_GUIDE.md), [learning notes](docs/LEARNING_NOTES.md) and [Atlas provenance](docs/ATLAS_PROVENANCE.md)

Selected MIT-licensed Atlas definitions and design conventions are reused with provenance. Atlas remains a separate, independently deployable reference. [License](LICENSE).

### Isolated OIDC visitor scenarios

The customer persona is **Subhanjan Das**. A forward migration preserves existing account IDs and ledger history. Invited OIDC users can receive separate customer-only synthetic accounts through the [operator provisioning runbook](docs/VISITOR_SCENARIOS.md), with atomic funding, repeat-request protection, capacity limits, expiry and deactivation. Public hosting and a real deployed identity provider remain pending.

## Public portfolio · zero-cost profile

The public build runs customer banking, business maker/checker approvals, employee operations, analytics, an instrumented recovery lab and architecture explorer. Synthetic scenarios persist in the visitor’s browser. [Runtime guarantees, walkthrough and deployment](docs/PUBLIC_DEMO.md). The original server profile retains OIDC, PostgreSQL and its independent test evidence. Public Pages publication status is recorded in [project state](docs/PROJECT_STATE.md).
