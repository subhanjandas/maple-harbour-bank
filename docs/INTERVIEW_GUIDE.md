# Interview walkthrough

## Opening

“Maple Harbour Bank is a synthetic Canadian banking application and data-engineering platform. I started with one traceable money-movement journey: owned-account authorization, locked funds, balanced immutable journals and an outbox commit together. A durable worker preserves source envelopes and publishes reconciled analytical activity with a cutoff and freshness. The UI distinguishes the running core from the planned distributed lakehouse, and I can demonstrate both failures and the limits of the tested topology.”

Built with AI assistance. Explain the code and evidence yourself; do not present this as employer infrastructure or a licensed bank.

## Five-minute demonstration

| Time | Show | Explain |
|---|---|---|
| 0:00–0:45 | Customer Alex's owned accounts and payment form | Synthetic CAD cents, booked vs available, backend authorization |
| 0:45–1:40 | Post CAD 125; open trace | Two balanced lines, three lifecycle versions, stable idempotency response and committed outbox |
| 1:40–2:30 | Taylor's operations workbench | Posting is not settlement; acknowledge simulator settlement, return CAD 30 with compensating journal |
| 2:30–3:20 | Jordan's analytical publication | Unique instruction vs version count, return grain, source cutoff, last-good version and freshness |
| 3:20–4:00 | Casey's engineering room and payment lineage | Actual backlog, archive receipt, ingestion run, publication run; Atlas evidence page remains a static reference |
| 4:00–5:00 | Architecture inspector and acceptance evidence | Source contract and boundaries, crash windows, hot-account contention, measured costs and remaining gates |

Sign out between personas. Production users cannot choose roles; this switcher is explicitly local-development authentication simulation. Open `evidence/` for the actual tested commit/results, not a claimed live screen capture from a cloud host.

## Questions to prepare for

**Why a modular monolith?** It keeps the accepted financial transaction atomic and minimizes coordination cost. Workers are separate because processing has a different lifecycle. Extracting a payment service without a clear owner/scaling/failure benefit would make correctness and operation harder.

**How do you prevent overspending?** Lock affected account rows in sorted order, read booked minus holds and post inside one transaction. The database verifies journal balance and account roll-forward. Kafka partition order would not protect two operational accounts.

**What happens if the client times out?** Retry exactly the same intent with the same actor-scoped idempotency key. If committed, the stored original response returns. A new key represents a new intent. Failed response caching is not yet implemented.

**Is this exactly once?** Delivery is at least once. An event ID/checksum prevents duplicate archive effects, source versions prevent double-counting and a transaction protects publication. Those are specific idempotent effects, not a universal exactly-once guarantee.

**How can yesterday change?** A later reporting-date revision changes the return attribution and republishes periods without changing cash. Money corrections require new postings. Do not sum all snapshots or join an original payment amount onto every installment.

**Why not put Spark everywhere immediately?** The first PostgreSQL prototype tests the semantic contract and failure boundaries cheaply. Spark/Delta and CDC/Kafka have different resource, storage and checkpoint responsibilities; introducing them requires a measured migration rather than a logo diagram.

**What did the benchmark achieve?** Distinguish generated source records, accepted bank commands, business effects, postings and lifecycle events. Quote a specific tested commit/hardware/distribution and all repetitions, including tail latency and variation. A million rows is not a million executed transfers.

**What failed during implementation?** The first real PostgreSQL run found a trigger record-field resolution bug that compilation could not catch. A forward migration fixed it. A later review found that FORCE RLS could hide ledger rows from an ordinary managed database owner; service/non-owner policies and a non-superuser migration test make that boundary explicit.

**What is left for production?** Real provider deployment, per-visitor isolation, organization approvals, full lakehouse/streaming integration, off-host archive/backup policy, image/action supply-chain hardening, broader security review and sustained multi-node capacity/recovery evidence. No regulatory certification is claimed.
