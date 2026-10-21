# Architecture decisions

## ADR · bounded public observatory (21 October 2026)

Use existing browser banking commands with a durable schedule/cursor, rather than fabricated charts or a second financial implementation. A generated cycle commits command effects and cursor together; retries use stable keys. Financial metrics come from approved Gold, operational telemetry from actual source/receipt state. This costs periodic bounded scans and per-device storage, and requires an open browser for progress. It can be omitted in the server profile. A shared backend is justified only when trusted multi-user coordination is required; distributed lakehouse tools require measured compatibility/resource evidence. [Component ownership, alternatives, costs and introduction gates](PLATFORM_VISION.md).

## ADR 001 · Connected core and analytical platform

Accepted for release 0.1. A modular monolith and PostgreSQL keep the first money-movement transaction atomic. A separately runnable durable worker gives independent processing and recovery. Service extraction requires a measured bottleneck, different ownership lifecycle or failure isolation benefit sufficient to pay for distributed consistency and operational cost.

## ADR 002 · Components, alternatives and operating cost

| Component | Responsibility and reason | Simpler alternative | Operational/resource cost | Omit or replace when |
|---|---|---|---|---|
| React + TypeScript | Role-aware application and explorer; common navigation and types | Server HTML | Build toolchain, dependency updates, browser bundle | Server rendering may suit a simpler app; retain for interactive trace/explorer |
| FastAPI | Validate commands, sessions, authorization and API contracts | Single Python script | API processes, connection pool, lifecycle and security upkeep | Script is insufficient for interactive trusted boundaries |
| PostgreSQL | Command authority, concurrency and immutable ledger; initial analytical prototype | SQLite | Durable disk, backups, WAL, connection limits; hot-row contention | SQLite is useful for offline examples, not this concurrent core |
| Polling outbox worker | Archive events and publish with idempotent effects | In-process background task | Poll queries, backlog, retained source history and separate process | Replace publisher at an audited cutoff when CDC/broker profile is justified |
| OIDC/Authlib | Authorization-code + PKCE identity; bank roles stay in DB | Local synthetic persona selector | Provider operations, discovery/JWKS availability and session lifecycle | Persona selector only in loopback development; never hosted |
| Debezium (planned) | Capture the outbox via PostgreSQL WAL | Polling worker | Connector JVM, replication slot, WAL growth and recovery controls | Omit in core; add for CDC learning/measured source read pressure |
| Kafka (planned) | Durable replayable stream and consumer isolation | Direct archive handoff | Broker disk, partitions, retention, monitoring; single broker has no HA | Omit until independent consumers/replay or measured throughput justifies it |
| Schema registry (planned) | Stream contract compatibility enforcement | Git-versioned JSON schemas | Service, schema subject policies, compatibility rollout | Git schema is enough before streaming producers/consumers exist |
| Spark / Structured Streaming (planned) | One engine owns lakehouse transformations and streaming | Current Python/SQL worker | Java/executor memory, checkpoints, startup overhead | Introduce only with tested 100K/1M replay and resource evidence |
| Delta Lake (planned) | Transactional lakehouse table snapshots and corrections | PostgreSQL prototype | Transaction log, compaction, retention, vacuum and object store semantics | Use with compatible Spark and durable storage; do not add a competing table engine |
| Object storage (planned) | Durable raw archive and lakehouse storage | Named local volume | Storage, requests, retention, egress and credentials | Local durable volume for development only; no arbitrary S3-compatible store assumption |
| Airflow (planned) | Own schedules and dependencies for batch/reconciliation/backfills | Single worker polling loop | Metadata DB, scheduler/API processes, operators and upgrades | Omit while one pipeline has no DAG complexity; no second orchestrator |
| OpenTelemetry (planned) | Distributed context and traces across future components | Current correlation IDs and structured logs | Collector/exporters, sampling and storage | Add instrumentation before claiming end-to-end distributed traces |
| Prometheus/Grafana (planned services) | Scrape operational gauges and inspect trends | Engineer API + restricted Prometheus-format gauge | Scraper retention, dashboard service, alert maintenance | Current role-protected `/api/metrics` is a small starting point; no alerting stack claimed |
| Playwright / pytest | Financial, access, recovery and real UI acceptance | Manual clicking | CI minutes, browser installation and fixture maintenance | Keep tests on actual boundaries rather than duplicating implementation |
| Docker Compose | Reproducible local services with separate credentials | Manual Python/PostgreSQL processes | Docker VM RAM/storage and image builds | Native startup is documented; not an HA orchestrator |
| GitHub Actions | Acceptance, actual captures and evidence artifacts | Manual checks | Public-runner usage/quotas, artifact retention, supply-chain trust | Keep verification reproducible outside CI |

No dbt, Snowflake, second stream processor or competing transformation scheduler is introduced.

## ADR 003 · Exact money and posting model

CAD only, exponent 2, signed 64-bit integer minor units at storage, positive command amounts capped at CAD 1M. Python command validation rejects floats, strings and booleans. Debits/credits are explicit positive journal lines. Deposit booked balance is credits minus debits; asset normal balance has the opposite sign. [Financial rules](DOMAIN_RULES.md).

## ADR 004 · Honest first analytical topology

Bronze/Silver/Gold concepts run in PostgreSQL to test source fidelity, versioning, correction and publication before adding a distributed stack. This shares a failure domain with the core. It is neither a lakehouse storage claim nor proof of cross-host recovery. Full replay favors clarity over scale; measure before optimizing incremental affected partitions.

## ADR 005 · Identity and hosted release gate

OIDC authorization code with PKCE uses Authlib. Short-lived opaque sessions can be revoked locally; roles/ownership never come from UI or arbitrary token claims. Fixed personas are allowed only in loopback development. Hosted deployment requires actual provider testing, separate visitor scenarios, TLS, secret management and restore evidence. Paid infrastructure additionally requires a monthly spending ceiling.

## Version/license compatibility review · 17 October 2026

Installed packages resolve from public PyPI/npm and are locked in `backend/uv.lock` and `web/package-lock.json`. React 19.3.1, Vite 8.3.4 and TypeScript 7.0.2 match the inspected Atlas/toolchain and build here. FastAPI 0.143.3 release notes were reviewed; Authlib 1.9.1 and psycopg 3.3.6 install with Python 3.12. The PostgreSQL 18.6 image and PostgreSQL license were checked at primary sources, then actually started in CI. Base images must be digest-locked before a hosted release; current tags alone are not a reproducible supply-chain guarantee.

Top-level licenses: React/FastAPI/Vite/Manrope package code and Atlas MIT (font files themselves OFL-1.1); TypeScript Apache-2.0; Authlib BSD-3-Clause; psycopg LGPL-3.0 with bundled dependency notices; PostgreSQL PostgreSQL License; lucide ISC; DM Sans/Manrope fonts OFL-1.1. Planned Kafka/Spark/Delta/Airflow/Debezium/Keycloak use Apache-2.0; planned Grafana introduces AGPL obligations and is not bundled here. This is a dependency inventory, not a legal certification.

Delta's current compatibility matrix lists 4.3.x with Spark 4.0.x/4.1.x. No Spark/Delta versions, CDC connector versions or object-storage compatibility are pinned or claimed tested in the core. Their introduction is a separate compatibility gate.

Primary references: [FastAPI releases](https://fastapi.tiangolo.com/release-notes/), [PostgreSQL 18.6](https://www.postgresql.org/docs/18/release-18-6.html), [PostgreSQL license](https://www.postgresql.org/about/licence/), [image tags](https://hub.docker.com/_/postgres/tags?name=bookworm), [Delta/Spark compatibility](https://docs.delta.io/releases/), [Debezium PostgreSQL](https://debezium.io/documentation/reference/stable/connectors/postgresql.html), [OIDC guide](https://www.keycloak.org/securing-apps/oidc-layers).

## ADR 006 · Managed PostgreSQL owner and row security

API and worker are distinct non-owner roles. Operational RLS is enabled for the API; a missing tenant binds no rows. The trusted schema owner intentionally bypasses those policies so deferred SECURITY DEFINER ledger checks can read all relevant lines. FORCE RLS was removed in forward migration 004 because an ordinary managed-database owner otherwise sees no permitted rows inside those checks. A superuser-only CI run would conceal that defect. Acceptance creates an ordinary non-superuser database owner, applies all migrations, seeds funding and verifies financial constraints. A provider must permit creation of service roles (or provision the equivalent separately) before its deployment is compatible.

## ADR 007 · Bounded synthetic source history

A scenario accepts at most 50K source events by default, with a 64KiB envelope limit and 100 return installments per payment. Exhaustion rolls back the complete command. A tenant counter introduces a serialization point; this is a deliberate small-demo resource policy, not a proposed production throughput technique. Keep it visible in benchmark versions and review it before scale work. No accepted event is discarded to satisfy retention.

## ADR 008 · Operator-admitted, customer-only visitor scenarios

A public visitor must not share the fixed development customer's money or select an employee role. The first hosted admission mechanism is an explicit schema-owner CLI that binds a provider-verified issuer/subject to a new synthetic tenant. Opening balances, identity, quota and audit evidence are atomic. A locked capacity row makes retries/capacity races predictable; provisioning is low-volume and serial admission is acceptable. All retained scenarios count toward capacity, so expiry cannot create unbounded stored history.

Automatic registration from any valid OIDC token was considered and deferred: a valid identity alone does not supply abuse controls, operator approval or a storage budget. No additional provisioning service, scheduler or dependency is required. Replace the CLI with a restricted, authenticated enrollment service only when invitation volume, audited operator separation or self-service controls justify that cost. Expiry gates future requests; immutable financial/source history remains preserved until a separately designed archival policy exists. [Exact commands and guarantees](VISITOR_SCENARIOS.md).

## ADR 009 · Zero-cost public profile

The owner requires a publicly accessible portfolio with a CAD 0 hosting budget. GitHub Pages serves the application, and a browser worker plus IndexedDB provides functional, persistent-per-device banking simulation. GitHub Actions tests the real PostgreSQL server as bounded CI work; it is not a permanent web server. The public role selector is explicitly a simulation, and the existing server security guarantees remain attached to the server profile. Business maker/checker is implemented in the public engine first and labelled separately in the capability matrix.

A paid persistent backend is no longer the default delivery gate. Free hosted database/function tiers were considered but would add another account, provider quota/suspension policies and shared-service abuse controls. The Pages profile requires no external credentials and isolates visitors by device. Its costs are bounded browser storage/CPU, duplicate domain implementations and no shared cross-device state. Contract/parity tests and precise runtime labels are required to manage that duplication. [Implementation and operating limits](PUBLIC_DEMO.md).
