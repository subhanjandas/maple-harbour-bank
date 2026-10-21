# Metric definitions

Release 0.4 adds an observed live dashboard. Its rates distinguish accepted command audits, new instructions, newly timestamped ledger lines, source events and archive receipts. Rates are trailing 60-second counts divided by 60; p95 is event-to-receipt latency over retained non-negative samples. Financial totals remain the last approved Gold version. See [exact definitions and coverage limitations](LIVE_OBSERVATORY.md).

Money is integer CAD cents. The daily fact grain is **Toronto business date × WEB channel × CAD currency**. No segment or customer SCD2 dimension is needed for this product. A later historical segment analysis must define valid/effective time, receipt time and an as-of join; joining today's segment to past activity is not acceptable.

| Metric | Definition / time attribution | Important exclusions |
|---|---|---|
| `instruction_count` | One accepted payment in latest POSTED/later state, on instruction business date | Initial lifecycle snapshots are not additional instructions; rejected commands not counted |
| `instruction_minor` | Original amount once per accepted payment | Not cash settlement volume; includes internal instructions in this first generic activity product |
| `return_count` | One current record per actual return installment, on its current reporting date | A new reporting revision is not another return |
| `return_minor` | Sum of installment amounts, current reporting attribution | Cannot exceed original payment; no report-date cash reposting |
| `settled_count` | Count of instructions currently SETTLED/PARTIALLY_RETURNED/RETURNED, attributed to original instruction date | Not a settlement-day fact, not settled cash flow; internal transfers are not settled |
| `reconciled` | Instruction and return amounts match independently read source latest-snapshot controls through cutoff | Not a universal ledger/rail completeness proof |
| `pending` | Committed outbox rows without archive acknowledgement | Not Kafka lag or number of banking transactions |
| `source_count` | Number of source lifecycle/revision events at publication cutoff | Three events are emitted for one new payment; never equate event count with transaction count |
| `freshness` | `current` only when refresh age is 0–60 seconds and no newer source events exist; otherwise `stale` | A no-change poll does not create a new refresh timestamp |

The operational account balance is directly queried from authoritative deposit state and checked against immutable ledger roll-forward. Analytical daily activity is not used to authorize spending. Account/customer analytical facts, failure-rate denominators and settlement-day metrics require separate products and documented grains; they are not fabricated from this table.

Every dashboard publication exposes publication ID, processing run, source cutoff/checksum/time, refresh timestamp and number of unpublished events. A rejected refresh leaves the last good publication available, with honest staleness. An unpublished database shows an empty state rather than zero activity presented as verified data.

Current `reconciled` specifically concerns event-source financial controls. Database journal balance and account-to-ledger constraints provide separate operational correctness evidence. A dedicated published ledger/control reconciliation fact is planned.
