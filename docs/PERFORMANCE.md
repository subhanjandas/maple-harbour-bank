# Performance evidence

No maximum transaction-per-second target or production capacity is claimed. `scripts/benchmark.py` measures two distinct workloads. Latest raw samples, plans, tested commit and hardware are in `evidence/benchmark.json`. The numerical baseline below is intentionally frozen at release 0.1; its [original raw report](https://github.com/subhanjandas/maple-harbour-bank/blob/c0fd0924328d1e5b8010652784a9d9851f2bd4b8/evidence/benchmark.json) and [original resource sample](https://github.com/subhanjandas/maple-harbour-bank/blob/c0fd0924328d1e5b8010652784a9d9851f2bd4b8/evidence/compose-resources.json) remain immutable. Release 0.2 reruns the same workloads; use each raw report’s source commit rather than comparing different runner samples as an optimization.

## Verified release baseline

Source commit `f7330756424c89f210cc98db08f6ba4490fb6ed5`, [CI run 39045330756](https://github.com/subhanjandas/maple-harbour-bank/actions/runs/39045330756). Ubuntu/Azure x86_64 runner, 4 reported CPUs, approximately 16GB memory, Python 3.12.15 and PostgreSQL 18.6. This baseline includes the scenario-counter quota and outbox column/RLS refinements. Newer evidence must be attributed to its own source commit, not silently substituted.

### Real banking-command baseline

Closed-loop HTTP workload: one hot customer account, eight concurrent request workers, CAD 0.01 outbound instructions, ten warm-up commands, then three repetitions of 100 distinct commands. The durable worker runs concurrently. These are accepted POSTED instructions, not 300 settlements.

| Repetition | Accepted commands/s | p50 ms | p95 ms | p99 ms | Errors |
|---|---:|---:|---:|---:|---:|
| 1 | 50.02 | 31.80 | 775.50 | 1167.83 | 0 |
| 2 | 115.25 | 24.37 | 265.37 | 482.60 | 0 |
| 3 | 105.86 | 26.19 | 201.13 | 698.14 | 0 |

Correctness checks: 300 distinct payment identities, 300-cent account reduction and 900 new lifecycle events; each instruction produces two payment journal lines. Measured units therefore differ: 300 accepted commands, 300 business effects, 600 payment postings and 900 events. Worker publication/outbox drain throughput is **not** inferred from this HTTP rate.

Tail latency and repetition variance are material. Ten warm-ups do not establish a steady-state maximum. Do not select a throughput claim from only the fastest repetition. Raw latency samples are retained for inspection.

### Deterministic analytical-record query baseline

Temporary isolated source-record fixture, **not banking transactions**. Values are deterministic modulo 365 business dates, with `amount=1+(i*7919)%100000` minor units. COPY loading and one selective day count/sum are measured. Each query variant has two warm-ups and five timed repetitions. An independent Python count/sum is checked after every query.

| Generated source records | COPY load seconds | Query p95 without index ms | Query p95 with index ms | Table bytes | Table + index bytes |
|---|---:|---:|---:|---:|---:|
| 100,000 | 0.0621 | 3.959 | 0.331 | 5,660,672 | 8,839,168 |
| 1,000,000 | 0.6405 | 49.907 | 8.413 | 52,330,496 | 83,894,272 |

This measures temp-table COPY/query behavior, not durable Bronze ingestion, Spark throughput, full replay, end-to-end analytical publication or real payments at those volumes. The covering index increases storage by approximately 60% for this narrow schema. It also adds build/write/maintenance cost; query plans and index-build times are in the raw report. No comparable index is automatically added to operational tables based on this microbenchmark alone.

## Resource observations

A single post-startup Compose sample recorded web ~5.0MiB, API ~51.0MiB, worker ~38.8MiB and PostgreSQL ~39.2MiB (about 134MiB combined). `evidence/compose-resources.json` is newline-delimited Docker JSON, not a single array. These are idle cgroup readings, not peak memory, working-set guarantees or evidence that the full lakehouse fits in 134MiB.

Declared runtime caps are web 128MiB, API/worker 512MiB each and PostgreSQL 1GiB. Docker Desktop VM/build requirements exceed observed idle memory; start with at least 4GB assigned to Docker for the core, then measure your laptop. The larger profile's minimum remains unmeasured.

The benchmark reports client peak RSS separately; it does not pretend client RSS equals server memory. Benchmark and container resource samples come from different explicitly identified runtime phases.

## Next measured gates

- Profile long-tail causes before optimizing; distinguish hot-row locking, connection pooling, request scheduling and worker competition.
- Measure backlog/drain rate and full-current-history rebuild cost as source history grows.
- Add duplicate storm latency, read/query/dashboard concurrency, cold-cache runs and sustained duration.
- Measure late-period correction and bounded selective backfill after implementing incremental affected partitions.
- Run broker/node failure only after an actual multi-node topology exists; current crash tests prove process recovery.

Every optimization must report workload, hardware/software identity, warm-up/repetitions, correctness, raw latency distribution and storage/maintenance trade-off. Raise the scenario quota only in an isolated lab after reviewing resource limits.
