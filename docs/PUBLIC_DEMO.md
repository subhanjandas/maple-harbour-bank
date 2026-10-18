# Public portfolio: zero-cost GitHub Pages profile

The public profile serves the same React application from GitHub Pages. A dedicated Web Worker executes banking commands and analytical processing, with IndexedDB persistence on the visitor's device. No paid account, backend token, real identity, payment information or external database is required. Synthetic activity belongs to that browser and does not affect another visitor. It survives reloads; clearing site data or browser eviction removes it. It does not sync between devices.

## Two honest runtime profiles

| Boundary | Public Pages simulation | Server lab |
|---|---|---|
| Hosting | Static GitHub Pages assets | Docker Compose on a local host or ephemeral CI runner |
| Commands | TypeScript worker messages | FastAPI HTTP API |
| State | IndexedDB atomic revision compare-and-set | PostgreSQL transactions and row locks |
| Identity | Per-tab synthetic role selection | OIDC relying party, opaque sessions, database roles and ownership |
| Processing | Browser Web Worker while the page is open | Separately runnable durable Python worker |
| Business approvals | Working simulated maker/checker, holds and organization scope | Not yet implemented |
| Data layers | SHA-256 envelopes, preserved Bronze, validated current Silver, atomic Gold publication | PostgreSQL medallion prototype with independent source controls |
| Recovery | Persisted archive/ack boundary, interruption and missing-source lab | Tested child-process failure, source completeness, backup/restore |
| Security claims | Educational role rules; device owner can inspect or change all browser state | Tested service grants, RLS, authorization, CSRF and OIDC validation |

The browser profile is not hosted PostgreSQL, production authentication, a real payment rail or a distributed lakehouse. These distinctions appear in the app and the architecture explorer. The server implementation is retained and tested independently. No secret is bundled into the public build.

## Working journeys

1. Enter as **Subhanjan Das**. Post a CAD beneficiary payment or own-account transfer. Inspect its ledger and event trace. Reopen the page and the accepted payment remains.
2. Enter as **Taylor Reid**. Simulate settlement and partial returns. Correct a return's reporting date; booked cash and original journals do not change. Internal transfer compensation checks destination availability.
3. Enter as **Avery Patel**, the business maker. Submit a supplier payment. Funds are reserved immediately as a hold. Enter as **Morgan Chen**, the checker, to approve or reject. Self-approval and cross-organization access fail in the command engine. Approval releases the hold and posts once; rejection releases the hold without posting.
4. Enter as **Jordan Martin** to inspect versioned daily activity, source cutoff and freshness. Instruction activity is never labelled settled cash flow.
5. Enter as **Casey Roy** to inspect actual worker runs and backlog. Pause the worker, post a payment, interrupt after the archive commit, then resume. Withhold a source record from refresh to see a rejected publication retain the last good result. Export actual scenario evidence as JSON.
6. In Architecture, switch between **Public demo** and **Server lab**. The selected topology is labelled as current or reference. Guided animation is illustrative; live evidence comes from actual scenario state.

## Financial and recovery semantics

Commands store exact safe integer CAD cents, currency exponent 2. Each committed state must have balanced journals, reconciled account balances, bounded holds and return totals no greater than the original payment. Commands, financial effects and outbox events commit together. Idempotency uses actor + key and canonical request contents; conflicting reuse is rejected. Financial history is append-only through the command interface. Browser developer tools can alter storage; this is not tamper-proof history against the visitor.

IndexedDB serializes its final read/write compare-and-set transaction across tabs. Computation and SHA-256 happen outside the transaction, then a revision check prevents lost updates. A conflict retries up to 20 times and then returns a retryable error. The worker message queue bounds execution within each tab. A retry after an uncertain response uses the original idempotency key.

Archive commit precedes acknowledgement. A resumed delivery checks stable event identity and does not duplicate Bronze. Publication validates the complete event identity/checksum set, schema marker/currency, sequential aggregate versions, and agreement with current operational snapshots and totals. Silver and the latest publication commit atomically. These browser validators are deliberately narrower than the server's Pydantic contracts; production schema compatibility belongs to the server/streaming profile.

Missing-source fault injection excludes one record from the publication input; it never destroys preserved evidence. Archive interruption is an instrumented pause at the actual durable boundary, not a broker/node-failure claim. Browser closure stops execution; reopening restarts the worker from stored events. The periodic worker sleeps when the published cutoff is unchanged.

Scenario limits: 500 payments, 5,000 events, 200 business proposals and 100 return installments per payment. Rejected transactions do not partially consume money. The whole-state store is a deliberate bounded portfolio choice, not a high-throughput database substitute. There is no automatic reset or destructive purge button.

## Build and publish

```bash
npm ci --prefix web
VITE_PUBLIC_DEMO=true VITE_BASE_PATH=/maple-harbour-bank/ npm run build --prefix web
```

`.github/workflows/pages.yml` tests browser journeys, builds the public profile, and uses official upload/deploy Pages actions on main. Repository Settings → Pages must select **GitHub Actions** once. Enabling Pages is an administrator setting, distinct from permission to push source. The connector used to write code does not expose that settings operation. No new token should be placed in the frontend or committed to solve it.

The same workflow preserves genuine screenshots and JSON test evidence. The public artifact includes a dated server CI evidence snapshot under `evidence/`; it is not live shared financial state. Standard GitHub-hosted runners for this public repository are free. Pages and test artifacts expire after one day to bound storage; no larger runners or paid services are used. This portfolio is synthetic and non-commercial, within the intended project-showcase use of Pages.

Primary platform references: [Pages hosting](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), [limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## What remains

The public app is a connected banking simulator, not the entire bank capability matrix. Cards, loans, fraud/disputes, statements/interest, independent batch sources and Spark/Delta/CDC remain unimplemented. The agreed cloud budget is **CAD 0**; future expansion must retain a runnable zero-cost public profile. Full database and scale experiments run locally or as bounded legitimate CI tests, not by keeping Actions jobs alive as a public backend.
