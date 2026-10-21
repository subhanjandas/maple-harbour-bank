# Maple Harbour Bank: connected banking and data platform

The project demonstrates engineering judgment by connecting accepted banking commands to exact postings, preserved events, validated analytical products and inspectable recovery. Release 0.4 deepens that path with a live observatory and reproducible source simulator. The public deployment budget is **CAD 0**. Broader banking realism is delivered through tested domain increments; the capability matrix remains the authority for implemented versus planned scope.

## Architecture: authoritative core plus medallion analytics

| Layer | Ownership | Current implementation | Target expansion |
|---|---|---|---|
| Operational core | Command acceptance, funds, holds, idempotency, ledger and audit | FastAPI/PostgreSQL server lab; public browser command simulator | Business approvals, cards and lending using explicit domain boundaries |
| Source/outbox | Financial transaction and source event commit consistently | Transactional outbox; polling/worker archive | One-publisher migration to Debezium/Kafka with the same server identities |
| Bronze | Original envelopes/files, source offsets, checksums, receipt/run identities | Preserved PostgreSQL/browser records | Durable object storage/Delta and controlled batch manifests |
| Silver | Contract/lifecycle/reference checks, duplicates, quarantine, current and history separation | Versioned history/current prototype; source and money controls | Spark Structured Streaming/SQL with replay and late-correction policy |
| Gold | Explicit grain, metric semantics, reconciliation, publication identity | Versioned daily payment/return activity | Payment control facts, loan allocation, card settlement and approved business products |
| Serving | Last-good publication, source cutoff, freshness and access policy | Approved APIs or browser role simulation | Restricted analytical serving models; raw layers never directly exposed |
| Observability | Distinct rates, lag, completeness, lineage, failures and evidence | Live browser observatory plus actual server CI evidence | OpenTelemetry and Prometheus/Grafana in a resource-reviewed lab |

Medallion is the data-quality architecture; it does not replace the transactional core. Accounts used for spending are never read from an eventually consistent Gold balance. A new lifecycle version is not another payment. Corrections preserve original money movement and rebuild the appropriate reporting attribution.

## Technology responsibilities and costs

| Component | Why it exists / what it owns | Simpler option now | Resource/operational cost and replacement gate |
|---|---|---|---|
| React + TypeScript | Unified role-aware banking/engineering experience | One existing app, no duplicated portal | Browser bundle and UI maintenance; split only for distinct product/ownership needs |
| FastAPI modular monolith | Trusted commands and server authorization | Explicit Python modules | API process/pool; extract a service only for measured ownership/scaling/reliability need |
| PostgreSQL | Atomic funds, ledger constraints, idempotency and outbox | One database failure domain | Locks, storage, backups and migrations; replication is not automatic HA |
| Browser worker + IndexedDB | Free public per-device simulation and processing | No hosted backend/account | Bounded device CPU/storage, no cross-device sync or execution while closed; not a production security substitute |
| Durable polling worker | At-least-once archive and publication | Own the current single processing schedule | Database polling/rebuild cost; replace publisher only after lag/WAL/cutover tests |
| Debezium | Capture committed outbox changes, not arbitrary financial re-interpretation | Polling | Replication permissions, connector recovery, retained WAL and slot monitoring; omit in the core profile |
| Kafka | Durable transport, backpressure and independently replayable consumers | Direct durable outbox/archive | Broker RAM/storage, retention and offsets; one broker is not HA; introduce for demonstrated fan-out/replay requirements |
| Spark/PySpark + Delta | Large batch/stream processing and durable lakehouse tables | Python/SQL prototype | JVM/executor memory, checkpoint/state, file sizing and compaction; one engine owns transformations |
| Airflow | Schedules, dependencies and bounded backfills | Current worker loop/explicit CLI | Scheduler and metadata services; Spark owns transformation logic, not a second competing orchestrator |
| OpenTelemetry + Prometheus/Grafana | Correlated traces, rates, lag, alert evidence | Structured logs/control room | Cardinality/retention and extra processes; add after an instrumented workload justifies them |
| GitHub Actions + Pages | Free public portfolio delivery and bounded legitimate lab tests | Standard public runners | Artifact retention and provider limits; never run a permanent API by keeping CI alive |

No dbt, Snowflake, competing stream engine or second orchestrator is introduced. Licenses and exact runtime locks are documented in DECISIONS.md. The planned distributed components are not silently bundled into the public app.

## Sources and APIs

| Source | Current status | Contract and failure behaviour |
|---|---|---|
| Customer and employee application commands | Implemented | Exact CAD cents, authorization/ownership, idempotency, balanced postings and same-transaction outbox |
| Seeded payment/settlement/return simulator | Implemented in public profile | Durable seed/cursor, bounded schedule, duplicate retries, source label and shared command implementation; exhaustion rolls back a cycle |
| Bank of Canada Valet reference series FXUSDCAD | Server reference CLI/cache implemented | Indicative CAD per USD; source/capture provenance, cache/timeout/bounded retries; no synthetic substitution during outage |
| CSV/JSON/Parquet settlement/control reports | Planned | Producer manifests, hashes, record counts, currency totals, reused-file-identity conflicts and complete-batch publication gate |
| Card authorization/clearing and merchant settlement | Planned simulator | Separate authorization holds and settlement cash, duplicates/delay/corrections/outages; no real card rails |
| Loan servicing and identity/fraud outcomes | Planned simulator | Deterministic source identities and lifecycle contracts; no real customer data or identity service claim |

The server source `mhb-core` and browser `mhb-browser-simulation` remain distinct contracts. Offline fixtures are labelled with provenance. A public browser export is evidence from an isolated simulation, not a trusted external core-banking feed.

## Banking domains: the next connected journeys

| Journey | Correctness/security question | Data product and acceptance evidence |
|---|---|---|
| Business approvals in PostgreSQL | Separate maker/checker identities, organization membership, holds and rejected approval release | Approval-cycle fact and fund roll-forward; backend organization/self-approval attacks |
| Cards: authorization → clearing → dispute | Hold expiry, incremental authorization, partial clearing, late presentment and chargeback compensation | Authorization/settlement performance, merchant reconciliation and dispute lineage |
| Loans: disbursement → repayment → arrears | Principal/interest allocation, schedule/version rules, due dates and overpayment | Loan balance/arrears facts; exact allocation and late correction tests |
| Customer service and fraud | Case scopes, evidence retention, decision/audit history and false-positive handling | Case aging, alert dispositions, traceable simulated outcomes |
| Fees, interest and statements | Calendar/day-count conventions, exact rounding, corrections and reproducibility | Statement snapshots and accrual/control reconciliation |
| Cross-border/reference FX | Canadian resident/non-resident context, indicative rates versus quotes, explicit currency postings | Currency-specific controls; no India-specific NRI products |

SCD2 is used only when historical attribution requires it, with effective/receipt time and as-of join rules. Neither creating empty screens nor importing every Atlas table constitutes an implemented domain.

## Scale and resilience gates

Keep commands/s, business instructions/s, ledger lines/s, source events/s, archive/analytical records/s and query concurrency separate. The public generator has a deliberately bounded cadence; it cannot establish maximum capacity. The existing server benchmark measures real accepted commands, and the 100K/1M fixture measures source-record queries. They are not interchangeable.

Next scale experiments should measure sustained hot-account contention, duplicate storm latency, backlog/drain, full-history rebuilds, late correction/backfill cost and dashboard concurrency. Each report must include hardware, source/software identity, distribution, warm-up/repetitions, p50/p95/p99, errors, invariants and resource usage. Optimize one observed bottleneck, then report storage and maintenance cost. Distributed topology failure tests require actual nodes/brokers; process interruption is labelled separately.

## Compatibility review · 21 October 2026

No new runtime dependency is needed for the observatory. Current official Delta documentation lists Delta 4.3.x compatible with Spark 4.0.x/4.1.x; exact pins, storage semantics and connectors still require an executed compatibility profile before introduction. Debezium's PostgreSQL documentation identifies retained replication-slot WAL as a disk-growth risk. Airflow's current architecture keeps scheduling/execution ownership explicit; it does not remove the need for idempotent Spark sinks and versioned publication.

Primary references: [Delta compatibility](https://docs.delta.io/releases/), [Delta table feature compatibility](https://docs.delta.io/versioning/), [Debezium PostgreSQL](https://debezium.io/documentation/reference/stable/connectors/postgresql.html), [Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html), [Airflow architecture](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html), [Spark SQL operator](https://airflow.apache.org/docs/apache-airflow-providers-apache-spark/stable/_api/airflow/providers/apache/spark/operators/spark_sql/index.html).
