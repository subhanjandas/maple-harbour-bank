# Architecture

The first slice uses a modular FastAPI monolith and separately runnable worker. Its domains are identity/access, deposit accounts, payment commands, ledger, integration and analytical serving. These boundaries live in modules and database grants; they are not separately deployed microservices.

PostgreSQL is authoritative for accepted commands and financial postings. The React application cannot supply a trusted actor, role, organization or account balance. An opaque server session resolves the principal; every command checks its permissions inside the backend.

[Generated component topology](ARCHITECTURE_GENERATED.md) comes from `architecture/manifest.json`, which is also served by `/api/architecture` and imported by the interactive frontend. Components include status, ownership, inputs, outputs, trust boundary, contract and rationale. Planned components are visually distinguished and hidden by default.

## Command and settlement boundary

```mermaid
sequenceDiagram
  participant C as Customer
  participant A as API
  participant P as PostgreSQL
  participant W as Worker
  C->>A: Session, CSRF, instruction, idempotency key
  A->>P: Lock key and owned account rows
  A->>P: Validate funds; insert payment, journals, outbox
  P-->>A: Commit all effects
  A-->>C: Stored stable command response
  W->>P: Archive original outbox event
  W->>P: Commit archive, then acknowledge source
  W->>P: Validate source-complete snapshot; publish
```

A payment is POSTED when the deposit debit and clearing credit commit. An employee's explicitly labelled simulator acknowledgement creates a separate settlement journal. No network acknowledgement is invented by the API. Internal transfers atomically move between the same customer's owned accounts; a reversal requires remaining funds at the destination.

## Analytical boundary

Bronze preserves original envelopes, source sequence, checksum, receipt timestamp and ingestion run. Silver retains versioned history and a current payment projection. Gold aggregates one latest payment per instruction and one current record per return installment. Publication attaches an identity, source cutoff, source checksum and refresh time. A single transaction inserts the publication and advances its serving pointer; rejected refreshes do not replace it.

These are **PostgreSQL analytical prototype tables**, not a Delta Lake implementation. The target profile uses Debezium/Kafka, Structured Streaming, durable object storage, Delta tables and Airflow. Those components remain planned until connector compatibility, resource limits and replay guarantees are demonstrated. [Component decisions](DECISIONS.md).

## Serving

| Consumer | Authority | Freshness behavior |
|---|---|---|
| Customer account and spending commands | Operational accounts and ledger | Committed state; row locks protect availability |
| Customer/employee payment detail | Scoped operational API | Current payment state and instrumented lineage |
| Analyst dashboard | Last successfully published aggregate | Refresh age, source cutoff and unpublished-event count shown |
| Engineer control room | Actual outbox metadata and pipeline runs | Polls every 10 seconds; no illustrative live traffic |

A publication's age is based on its refresh; event source time is separately exposed. A no-change poll does not fabricate a fresh publication. The worker does not serve raw payloads to the browser.

## Fault boundaries

| Boundary | Mechanism | Limit |
|---|---|---|
| API → DB | One transaction and durable idempotency response | Ambiguous network result requires original key retry |
| DB → outbox | Same transaction | A schema owner can bypass service controls |
| Outbox → Bronze | Sink commit before ack, identity/checksum deduplication | Shared database host; no broker/node HA |
| Bronze → Silver | Strict schema, immutable history and version checks | Whole-history replay cost grows with retained events |
| Silver → Gold | Source totals and daily-grain aggregation | Reconciles to source event controls, not unseen real rails |
| Gold → serving | Atomic publication pointer | Analytical serving is eventually consistent |
| Serving → dashboard | Role check, freshness metadata, refresh action | Browser network failure can leave an older screen visible |

There is no CDC broker boundary in the core profile. Future migration must stop the poll publisher at an explicit cutoff, preserve event IDs and validate a replay before enabling the CDC publisher. Never assume partition order protects a transfer involving multiple accounts.

## Visitor identity boundary

The [operator-only provisioning CLI](VISITOR_SCENARIOS.md) uses a protected schema-owner connection to create a separate synthetic customer tenant, opening journals and quota atomically. The API cannot provision visitors or staff. A verified OIDC issuer/subject resolves to the stored principal, and scenario expiry is checked on each request. Approved analytical tables and the lineage metadata view require a bound tenant in addition to API role checks. The serving worker is intentionally authorized to process all admitted tenants. No additional runtime service is required for this low-volume invitation workflow.
