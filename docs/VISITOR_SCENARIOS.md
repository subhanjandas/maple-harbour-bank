# Isolated synthetic visitor scenarios

Release 0.2 adds an **operator-controlled admission path**, not public self-registration or real bank onboarding. Each verified `(OIDC issuer, subject)` maps to one new tenant and a customer-only principal. The subject is a provider's stable identifier; do not use an email address or a browser-supplied name to choose ownership. Token role/tenant claims do not grant permissions.

## Provision an invited visitor

Apply migrations 001–008 using the schema owner. Configure a real HTTPS OIDC provider separately, as described in [deployment](DEPLOYMENT.md). The production CLI accepts HTTPS issuer URLs only, and the exact issuer must match the API's configured issuer and the validated ID token. Signed local test-provider HTTP is enabled only by an internal test argument, not a CLI flag.

Create an ignored, protected request file under `.runtime/` (directory mode 700, file mode 600). Obtain the subject from the trusted provider's admin workflow. Example synthetic request:

```json
{
  "issuer": "https://identity.example/realms/maple-harbour",
  "subject": "provider-verified-synthetic-subject",
  "display_name": "Subhanjan Das",
  "operator_label": "approved-demo-operator",
  "lifetime_days": 7,
  "event_limit": 3000
}
```

With `MIGRATION_DATABASE_URL` supplied through protected operator configuration:

```bash
uv run --project backend python -m mhb.provision create --request-file .runtime/visitor.json
```

The command returns opaque principal/tenant IDs and whether it created them; it does not print identity claims or credentials. API/worker credentials cannot run it. Admission, accounts, opening journals, quota and administration evidence commit in **one transaction**. A failure rolls everything back. Do not expose schema-owner credentials to the API or web container.

Each visitor receives synthetic CAD 5,000 chequing and CAD 12,500 savings, a simulated energy beneficiary and separate cash/clearing ledger accounts. There is no real money movement. No employee, engineer or analyst principal is created. The visitor can post payments and inspect their own trace; settlement/returns remain a separately authorized operations workflow. A customer scenario is not an authorization shortcut to all workspaces.

## Idempotency, capacity and expiry

Admission locks a single capacity row. Concurrent repetitions of the same identity return the existing scenario, without additional opening journals or funds. A different requested name, quota or lifetime on a repeat does not silently reconfigure an existing identity. An identity already assigned outside the visitor registry is rejected. This small operator path deliberately serializes admission; it is not a high-volume onboarding design.

The default capacity is **100 retained scenarios**, including expired and disabled ones. Operators may set `visitor_capacity.scenario_limit` between 1 and 1,000 after reviewing storage and workload. Counting inactive scenarios prevents expiry from enabling unlimited database growth. Each visitor is limited to 3,000 source events by default, configurable at creation from 3 to 50,000. Existing atomic quota rollback protects the financial command if insufficient event capacity remains.

The maximum lifetime is 30 days; default seven. Session authentication and OIDC callback both consult scenario expiry/disable state in PostgreSQL. Expiry denies subsequent authenticated requests without waiting for session-cookie expiry or a cleanup schedule. An already authorized in-flight request may complete; this is request-boundary revocation, not cancellation of executing database transactions. Time is UTC. Lifetime is an access policy, **not a data deletion policy**.

## Deactivate without destroying evidence

```bash
uv run --project backend python -m mhb.provision deactivate \
  --tenant visitor-REPLACE-WITH-RETURNED-ID --operator-label approved-demo-operator
```

This atomically disables the principal/scenario and revokes its existing sessions. Repetition has no extra effect. A later create request for the same identity does not re-enable or re-fund it. Journals, payments, source history and publications remain intact for investigation. There is no browser reset/deactivation/provisioning endpoint. No reactivation or purge command is implemented.

The append-only `scenario_admin_events` table records admission/deactivation and an operator-supplied label. **The label is an attestation, not authenticated operator identity.** Schema-owner credential access and the deployment platform's operator audit logs are the actual boundary. Production enrollment would need a least-privilege provisioning service and independently authenticated administrator audit.

## Isolation and remaining gates

Operational RLS and ownership checks isolate visitor accounts and payments. Approved analytical tables and the owner-backed lineage metadata view are also tenant-filtered. The worker retains cross-tenant processing rights; the browser receives approved APIs only. Authentication's principal/session lookup must happen before a tenant is known and remains a trusted backend boundary. SQL tenant settings protect against missing filters; they do not protect against arbitrary compromise of API credentials and application code.

Acceptance covers simultaneous duplicate admission, competing admissions at capacity, injected opening-journal failure, two signed OIDC sessions, cross-visitor payment attempts, forged role/tenant claims, forbidden staff workspaces, expiry, deactivation and actual API/worker grants. Full evidence is linked in [test evidence](TEST_EVIDENCE.md).

This does not deploy a real IdP, implement self-service enrollment, implement business organization approvals, or provide timed archive/purge. Public launch still requires an approved budget and account, actual HTTPS/OIDC validation, bounded off-host retention, provider secrets/backup policies and deployed acceptance. Never enable the local persona selector on a public host.
