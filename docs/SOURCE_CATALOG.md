# Source catalog

Only implemented payment/deposit domains emit operational events. An account opening is currently explicit seed data rather than an operational onboarding journey.

| Source | Owner / contract | Frequency, delivery and expected volume | Classification | Failure behavior / status |
|---|---|---|---|---|
| Banking commands / payment snapshots | Banking core; `payment-snapshot-v1.schema.json` | Per accepted lifecycle change; three events at initial posting, then one per settlement/return/correction; at least once via outbox | Restricted synthetic banking | Transaction rolls back on validation/funds failure. Source event persists with command. Implemented. |
| Synthetic settlement acknowledgement | Integration/operations; settlement command | Explicit scoped employee/CLI action, not a scheduled real feed | Restricted synthetic | Idempotency and state check; rejected/duplicate requests tested. Simulated integration. |
| Synthetic return installments | Integration/operations; return command | Positive installments, cumulative amount bounded by original | Restricted synthetic | Duplicate key has no new effect; early/excess returns fail. Simulated integration. |
| Bank of Canada Valet FXUSDCAD | Reference data; official JSON observations | Business-daily indicative average, CAD per 1 USD; cache 24 hours; bounded 3 attempts and 5-second HTTP timeout | Public reference | Explicit stale cache on outage or unavailable without cache. Never synthetic fallback. CLI implemented; not used to execute FX. |
| Producer CSV/JSON/Parquet reports | External report producer; future independent file manifest | Controlled daily batches with file hash, count and financial totals; volumes not yet measured | Restricted synthetic | Planned: duplicate/missing/reused-ID/incomplete-batch gates. Not an implemented batch feed. |
| Card authorization/clearing, merchant settlement, loan servicing, fraud and identity verification | Future integration simulators | Deterministic seeded sources with duplicates, delay, outage and correction controls | Restricted synthetic | Planned; no operational events or integration claims for these domains. |

Current payment source-completeness controls come from the committed outbox, independently read from Bronze. They establish fidelity relative to that known source log; they do not prove an upstream external institution supplied everything. `receipt time` and `event time` are separate fields.

## Bank of Canada evidence

The recorded offline fixture is `fixtures/reference/boc-fxusdcad-2026-10-16.json`; adjacent provenance includes exact URL, capture timestamp and SHA-256. It is an actual captured public response, not a fabricated rate. `FXUSDCAD` reports Canadian dollars per one US dollar. Daily averages are normally published by 16:30 ET on Bank business days and may be delayed; weekends/holidays are not silently filled.

CLI (from `backend/`):

```bash
uv run python -m mhb.reference --cache ../.runtime/boc-fx.json
```

The cache stores original source identity and observations; returned status distinguishes fetched, cached and stale-source-unavailable. No frontend payment uses a reference rate as an executable quote. Future FX must have an independent quote identity, price/fee policy, expiry and supported-currency exponent.

Read and respect [Valet guidance](https://www.bankofcanada.ca/valet-api-how-to/), [series documentation](https://www.bankofcanada.ca/valet/docs), [publication conventions](https://www.bankofcanada.ca/rates/exchange/daily-exchange-rates/) and [source terms](https://www.bankofcanada.ca/terms/). Attribution is to the Bank of Canada, with no endorsement. Source terms are separate from the repository's software license. The source is not guaranteed accurate or complete.
