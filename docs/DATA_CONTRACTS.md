# Data contracts and replay

The operational outbox publishes `payment.snapshot`, schema version 1. `contracts/payment-snapshot-v1.schema.json` is generated from Pydantic models in `backend/mhb/contracts.py`; unknown fields and unknown versions are rejected. An additive optional field still requires a deliberate compatibility review because the current v1 reader is strict. Do not silently relax financial semantics.

## Event and archive evidence

| Field | Meaning |
|---|---|
| `source_system`, `event_type` | `mhb-core`, `payment.snapshot`; only implemented domain |
| `event_id` | Immutable UUID delivery identity; duplicate must retain checksum |
| `aggregate_id`, `aggregate_version` | Payment identity and monotonic lifecycle/revision sequence |
| `schema_version` | Strict source schema version, initially 1 |
| `tenant_id` | Source scenario boundary; must match payload tenant |
| `event_time` | Offset-aware source event timestamp |
| `correlation_id`, `causation_id` | Original journey context and producing command/preceding event |
| `currency`, `currency_exponent` | CAD, 2; amounts remain integers |
| `payload` | Payment snapshot plus all known return installments with booked/reporting dates and revisions |
| `reason` | Command, simulator acknowledgement or reporting-date correction |
| `outbox.seq` | Durable source sequence; allocation order is not a global commit-order guarantee |
| `bronze.received_at` | Database archive receipt time, distinct from event time |
| `bronze.checksum` | SHA-256 of canonical original envelope |
| `bronze.ingestion_run_id` | Archive operation identity, retained on duplicate delivery |

Batch/file identity is not applicable to these operational events. There is no fictitious file offset or Kafka offset in the contract. External batch sources require their own independent manifest when implemented.

## Bronze

Append-only original event envelopes, source sequence, checksum, receipt time and run ID. A sink commit can precede acknowledgement; redelivery encounters the same unique event and checksum. API credentials cannot read Bronze. No raw-query endpoint exists. The single PostgreSQL host is a shared failure domain; this is not a cloud object archive.

## Silver

Immutable event history is separate from `silver_current`. Projection uses the highest aggregate version, not receipt order. Validation checks identity agreement, positive exact amounts, CAD conventions, return totals, immutable parent/business fields, contiguous source versions and allowed lifecycle transitions. An older delivery does not downgrade state. Equal identity with different content is rejected.

A source snapshot is a version of one payment, not another payment transaction. A reporting correction may preserve state and cash while changing a return's reporting date. Historical events are never overwritten. There is no speculative customer entity-resolution algorithm or customer segment SCD2.

## Gold and publication

Grain is business date × WEB × CAD. Payments and returns are aggregated separately into one daily union, preventing one-payment/many-return fan-out. Historical date corrections rebuild all current daily partitions at this scale, which updates old and new periods correctly but has growing full-replay cost.

For each attempt, the worker independently captures source sequence/event/checksum controls under a repeatable-read snapshot. Bronze must match that source identity set through its cutoff. Source financial totals from latest snapshots must match Gold. A failed check creates a rejected run/quarantine code and preserves the last successful pointer. A successful transaction stores immutable publication content and advances the pointer together.

`publications.id` is the serving version. It records source cutoff, source count/checksum, cutoff event timestamp, refresh timestamp and run ID. No stale result is silently passed off as current.

## Quarantine, replay and limits

Malformed source records stay in the access-controlled archive; reason codes are stored separately. A bad record blocks publication rather than silently dropping financial activity. Controlled poison-record disposition and schema migration tooling are not yet implemented: investigate the preserved source and issue a reviewed contract-compatible producer repair before claiming recovery. Do not mutate original source evidence to make a check green.

The worker can replay preserved source events and rebuild projections. A crash within the publication transaction rolls back projection/publication changes; a crash after archive commit leaves an unacknowledged source row for safe redelivery. The tests exercise actual child-process exits at both points.

The CLI backfill command accepts 1–31 business dates but currently performs a full-current-state rebuild. It is a bounded operator request, **not** a bounded computation optimization. Selective affected-partition backfills, arbitrary externally supplied batch imports and consumer offset checkpoints are future work.
