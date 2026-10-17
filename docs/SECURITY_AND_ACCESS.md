# Security and access

This is a synthetic banking simulation. Controls are implemented and tested at selected boundaries; regulatory certification, production hardening and a complete banking security program are not claimed.

## Trust boundaries

```mermaid
flowchart TD
  Browser["Untrusted browser"] -->|"HTTPS, opaque cookie, CSRF"| API["Trusted API service"]
  IdP["Configured OIDC issuer"] -->|"Code + PKCE, signed ID token"| API
  API -->|"API login, tenant context, row policies"| Core["Restricted operational data"]
  Core -->|"Committed immutable envelopes"| Outbox["Outbox"]
  Worker["Separate worker login"] -->|"No account writes"| Outbox
  Worker --> Raw["Restricted Bronze and Silver"]
  Raw --> Published["Approved publication"]
  Published -->|"Authorized serving API"| Browser
  Operator["Restricted migration / backup credentials"] --> Core
```

## Implemented controls

- Authlib OIDC authorization code with PKCE, state, nonce and signed ID-token validation. A provisioned `(issuer, subject)` maps to a bank principal; roles/scopes come from the database. No password grant or browser-selected role is trusted.
- Opaque random 30-minute server sessions; only token/CSRF hashes stored. Session cookie is HttpOnly, SameSite Lax, Secure in hosted mode. CSRF header and exact Origin are checked on mutations. Logout revokes the session record.
- Production startup rejects development persona authentication, insecure cookies, non-HTTPS origins or non-HTTPS OIDC issuer. Fixed persona login only exists in development with a configured loopback origin. Compose exposes only its web port on loopback.
- Customer ownership, employee team scope and synthetic tenant checks. Row policies on operational tables fail closed without a transaction-bound tenant. Roles, ledger writes and pipeline access are not only UI restrictions.
- Distinct schema-owner, API and worker database logins. API cannot read raw Bronze or write analytical publications; worker cannot read customer account/session tables or change financial postings. Neither can migrate.
- Parameterized SQL and strict Pydantic command/event contracts. Explicit integer limits, lock/statement timeouts, bounded pool and retry count.
- Durable per-principal request counters (shared across API processes), login limits, same-origin reverse proxy, request body size limit and browser security headers.
- Append-only audit, journal, financial history and source archive. Logs contain normalized route, status, duration and request ID, not token, body, account number or full customer name.
- Local random secrets are generated into ignored mode-600 `.env`; no supplied credentials are committed. Dependency audits and a small tracked-source secret guard run in CI. The latter complements rather than replaces a comprehensive secret scanner.

## Role matrix

| Role | Allowed | Denied |
|---|---|---|
| Customer | Own accounts, beneficiaries, instructions and their traces | Other customers, staff analytics, settlement/return commands, control room, raw data |
| Operations | Payments in assigned scope; simulated settlement/returns; approved aggregate analytics | Different scope/tenant, customer spending commands, engineering controls/raw data |
| Analyst | Published tenant aggregates | Customer command/detail APIs, raw archive, operations and backfills |
| Engineer | Tenant publication/run metadata, outbox backlog and approved aggregates | Customer spending, settlement/returns, raw payload query, unrestricted browser backfill/reset |
| Operator CLI | Explicit migrate, seed, worker, backup/restore or backfill credential | No claim that a filesystem owner or schema administrator is constrained by application policies |

Business organization membership and maker/checker separation are not implemented. Synthetic tenant isolation is tested, but must not be described as business-banking approval enforcement.

## Threat model

| Threat | Control / tested boundary | Remaining requirement |
|---|---|---|
| Customer guesses another payment/account ID | Ownership+tenant filters; 404 outside visibility | Broader ID enumeration/rate-abuse testing |
| Forged role or customer identity | Identity from database session, not request body | Real provider deployment/provisioning process |
| Session theft/CSRF | HttpOnly/Secure/SameSite, exact Origin, CSRF, expiry and revocation | Idle expiry, device/session UI, MFA, provider back-channel logout |
| Concurrent overspending / duplicate storm | Locked funds and key; actual concurrent tests | Multi-node sustained load and capacity limits |
| Employee overreach | Scope checks in command and detail/list APIs | Segregation of duties, privileged-access review and case-assignment policy |
| Analytical/raw leakage | Separate DB grants, no raw browser endpoint | Hosted IAM, encrypted backups, network policy, managed secrets |
| Public abuse of reset/load/failure injection | No such browser endpoints; local selector disabled hosted | Per-visitor scenario isolation before public release; edge protection |
| Supply-chain or secret leakage | Lockfiles, package audits, small source guard | Digest-pinned images, action SHA pinning, comprehensive scanning and signing |
| Database administrator rewrites evidence | Service roles cannot mutate posted records | Off-host immutable audit/archive and independent operational controls |

OIDC integration tests use a real local HTTP code exchange and signed tokens from a **test provider**, including wrong issuer/audience/nonce/signature/expiry. They do not certify a deployed Keycloak/Entra configuration.

## Public release gate

No public deployment is enabled by this increment. Before publishing: isolate each visitor's synthetic scenario; complete a real provider integration and session lifecycle review; configure TLS and secret storage; verify network and service credentials; run backup/restore; bound retention and load; and obtain a paid-resource ceiling if hosting incurs charges. Do not expose the local persona selector or engineering CLI credentials to public visitors.

Forward migration 005 also restricts the API to tenant-scoped outbox **metadata**. It has no SELECT permission on original source envelopes/checksums, although it inserts them as part of the command. The trusted worker alone reads the full source contract for processing; its UPDATE grant is restricted to acknowledgement/retry columns.
