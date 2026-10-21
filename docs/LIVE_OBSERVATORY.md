# Live banking and data observatory · release 0.4

The public app's **Live dashboard** connects actual synthetic command effects, event arrivals, archive receipts and approved publications. Jordan opens the observatory by default; Taylor and Casey can use its navigation entry. Customer/business personas cannot query staff telemetry. Casey alone can schedule or control workloads. Browser roles demonstrate workflow scope; they do not create a security boundary against the device owner.

## Reproducible source activity

A workload stores its ID, seed, requested instruction count, interval, next tick, completed cursor, payment IDs, duplicate requests and terminal disposition. Only one running or paused workload is allowed. Each has 1–40 instructions, an interval from 1–10 seconds, and at most ten retained runs per scenario. Existing payment/event/funds limits still apply. No run resets balances, refunds prior activity or bypasses quotas.

The deterministic amount for zero-based index `i` is `100 + ((seed XOR low32((i+1)*0x9e3779b1)) mod 2401)` CAD cents, with unsigned 32-bit XOR. Seed 42 starts with **685, 416, 1087, 826 cents**. Each cycle posts an outbound payment and a simulated settlement; every third instruction returns `floor(amount/4)` cents. Every fourth instruction repeats its original payment key and receives the original response. IDs and timestamps are newly generated; reproducibility refers to amounts and action distribution, not identical wall-clock traces.

Generation uses the same payment, idempotency and operation implementations as the interface. One cycle's commands, journals, source events and durable cursor commit atomically. The cycle's atomicity deliberately includes an immediate settlement simulator acknowledgement; it does not claim realistic network settlement delay. If funds or event capacity are exhausted, the financial transaction rolls back and a separate metadata transaction marks the workload failed. Previously accepted cycles remain intact.

One cycle runs per eligible worker tick. There is no burst to catch up after browser sleep or closure. Pausing generation preserves its cursor; pausing the pipeline independently allows source backlog to build. Another tab competes through the same IndexedDB revision check, so only one cursor/effect commits. A stop prevents subsequent ticks; an already committed cycle remains accepted.

## Metric dictionary

| Metric | Exact source and grain | Interpretation |
|---|---|---|
| Approved instruction and return CAD | Last successful Gold publication | No financial dashboard total is calculated from unapproved events |
| Operational instructions | Current command-side payments | Includes accepted but not yet published instructions; never a spend authorization |
| Accepted banking commands/s | Successful unique payment/lifecycle/business mutation audit records in trailing 60 seconds ÷ 60 | Duplicate requests are separate from accepted effects; simulator scheduling/control is excluded |
| Unique instructions/s | Payment creation timestamps in trailing 60 seconds ÷ 60 | One payment is one instruction despite multiple lifecycle snapshots |
| Ledger lines/s | New timestamped non-opening journal lines in trailing 60 seconds ÷ 60 | Two lines per simple posting; not a business transaction rate |
| Source events/s | Envelope event time in trailing 60 seconds ÷ 60 | Lifecycle snapshot events, not new payments |
| Archive records/s | Bronze receipt time in trailing 60 seconds ÷ 60 | Ingestion receipt rate, not total Spark/Delta processing throughput |
| Archive p50/p95/p99 | Receipt minus event time, nearest-rank over valid preserved receipt samples | Event-to-archive delay, not HTTP API latency; clock-negative samples excluded |
| Pending/oldest age | Unacknowledged events and age of the earliest event time | Archive delivery backlog; archived-before-ack records can remain pending during recovery |
| Unpublished events | Source count beyond last approved cutoff | Separate from archive backlog and refresh age |
| Freshness | Publication age ≤60 seconds and no events beyond cutoff | Quiet old publications can be complete but age-stale; no heartbeat pretends to refresh them |
| Source coverage | Unique preserved Bronze records / source events | Completeness indicator; validation/publication controls remain independently required |
| Rejected/successful runs | Retained run history, maximum 100 | Not lifetime totals |

Charts have twelve exact count buckets using event time and receipt time respectively. Time windows and lifecycle filters are interactive. An accessible table exposes the plotted counts. The dashboard reads every two seconds while visible, with no overlapping request. The application never increments a counter or animates a flow to fabricate telemetry.

## Actual architecture and lineage

Architecture has three distinct modes: intended/implemented topology, explicitly illustrative guided simulation, and actual live evidence. The evidence mode reads the same telemetry contract as the dashboard. It shows ledger **lines**, source/archive **events**, Silver **current aggregates** and Gold **current publication** with their different grains.

Selecting an approved payment creates a deep link with `mode=evidence&payment=<id>`. The view traces original event/version/sequence through archive receipt and ingestion run to validated state and the publication/run IDs. Deep links share UI state, not private scenario data; another browser has a different isolated scenario.

Both public and server topology diagrams are generated into documentation and README from the manifests used by the explorer:

```bash
python3 scripts/render_architecture.py
```

## Compatibility and scope

State schema v1 evolves additively: old scenarios can lack `workloads` and journal `created_at`. Such scenarios remain usable. Historical untimed ledger lines are excluded from rate calculations and explicitly counted as uncovered legacy rows. No existing journal, payment or event is rewritten just to add telemetry.

The public browser is a bounded observability demonstration. Server OIDC/RLS/concurrency evidence remains separate. No maximum TPS, broker/node resilience or distributed lakehouse deployment is claimed. Full server benchmarks and 100K/1M query baselines retain their original workload/hardware/source identity in PERFORMANCE.md and raw reports.
