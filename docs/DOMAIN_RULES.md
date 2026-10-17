# Domain rules and financial semantics

All money and identities are synthetic. CAD is the only implemented currency, with exponent 2. Command amounts are positive integer cents and at most 100,000,000 minor units. Never authorize spending using analytical state.

## Balances and ledger

A deposit account is a bank liability. `booked_minor` equals its lifetime journal credits minus debits, including synthetic opening funding. Available is booked minus held funds; no overdraft is implemented. Hold fields and constraints exist but creating/releasing holds is not an implemented workflow.

| Event | Debit | Credit | Customer effect |
|---|---|---|---|
| Synthetic opening | Simulated cash asset | Deposit liability | Increase booked/available |
| Outbound payment posting | Deposit liability | Outbound clearing liability | Reduce booked/available immediately |
| Settlement acknowledgement | Outbound clearing liability | Simulated cash asset | No second deposit debit |
| Partial return | Simulated cash asset | Original deposit liability | Increase booked/available by the installment |
| Internal transfer | Source deposit liability | Destination deposit liability | Atomic transfer, only within the customer's owned accounts |
| Internal reversal | Original destination liability | Original source liability | Exact opposite movement; require destination funds |

Each journal is single-currency CAD with at least two positive lines and equal total debits/credits. Deferred constraints check balance at commit. Deposit roll-forward is independently checked against ledger lines. Updates/deletes are rejected; adding lines to an already committed journal is rejected too. Monetary corrections require a new journal.

The simplified clearing/cash chart is a simulation, not a full bank general ledger, liquidity engine or prudential report.

## Commands and concurrency

The backend resolves a session principal, checks role and owned/scope/tenant resources, acquires a transaction-scoped lock on actor/tenant/idempotency key, then locks affected account rows in sorted ID order. The funds check and all journal/account/outbox writes are in the same PostgreSQL transaction. Payment operations also lock the payment first. Small bounded deadlock/serialization retries retain the original key; lock timeouts return a retryable 503.

`Idempotency-Key` is required (8–100 characters). The key is scoped to actor and tenant, and binds action plus canonical payload. The original committed response is stored, so a duplicate still returns the same response after a payment later settles. Reusing the key with different content returns 409. Failed commands roll back; stable failure-response caching is not yet implemented.

Kafka ordering is irrelevant to the operational locking guarantee. Exactly-once delivery is not claimed.

## Lifecycle

Customer creation records RECEIVED → VALIDATED → POSTED inside one accepted transaction. No partial accepted instruction is visible if validation fails. An outbound POSTED instruction can be SETTLED by a scoped operations simulator. A settled payment can receive positive installments up to its original amount: PARTIALLY_RETURNED until equal, then RETURNED. An internal POSTED transfer can be REVERSED once; reversal of reversal is unsupported.

Returned amounts and the return's immutable payment parent are checked. A reporting-date correction increments the aggregate and return revision; preserves amount, original booked date and journals; and publishes a new historical analytical attribution. This is a metadata correction, not a new payment or new cash movement. Date must fall within the payment's lifetime and not in the future. Monetary return revision is not implemented.

## Time

Timestamps carry explicit UTC offsets. Business dates derive from `America/Toronto`, including daylight saving rules. Display timestamps are labelled ET; a date-only source attribution remains a business date. Settlement calendars, cutoff policies, interest, fees and statement cycles are planned.

## Identity and organizations

The first customer model has one owner per deposit account. Employees have a Toronto/Vancouver team scope. Synthetic tenant isolation is implemented; business organization membership, maker/checker approvals and joint ownership are **not implemented**. Tenant tests do not constitute business-approval coverage.
