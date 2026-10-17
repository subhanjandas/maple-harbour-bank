# Deployment and economics

## Verified deployment state

The core containers build, migrate, seed and pass readiness checks on a GitHub Actions runner. Browser acceptance uses a real API, worker and PostgreSQL. These ephemeral test deployments stop at the end of the run. **There is no persistent hosted banking URL.** Atlas's public static site remains independent and unchanged.

`compose.yaml`, both Dockerfiles, SQL migrations and the isolated lab override are version controlled. No paid infrastructure or cloud account has been provisioned. Provider-specific infrastructure-as-code awaits a compatible provider/account and explicit spending ceiling; a misleading deploy button for an ineligible topology is not supplied.

## Proposed persistent public topology

One same-origin web/API endpoint, a separately runnable worker and a persistent PostgreSQL database. Keep operational/analytical paths explicit; the initial public topology would still use the PostgreSQL prototype, not secretly pretend to operate Kafka/Spark/Delta. The architecture manifest must be updated to the actual hosted topology before publication.

Gate sequence:

1. Confirm ordinary database-owner migrations and service role support on the chosen provider.
2. Configure a real OIDC issuer/client, exact callback URL, provisioned subject mapping, secure cookies and HTTPS; keep secrets in provider-managed runtime configuration.
3. Implement per-visitor synthetic scenario isolation and quota/retention. Public users must not select shared employee/admin identities.
4. Validate the entire HTTP payment/settlement/return/processing path and a backup restore using the deployment image.
5. Record cost ceiling, network, backup, retention and shutdown instructions. Provision only after budget is authorized.
6. Publish, run deployed smoke checks, record URLs and exact image/source identities in project state.

OIDC code-flow tests against a signed test provider are useful relying-party evidence, not a replacement for a real deployed provider configuration. Fixed local personas are disabled in non-development mode and must never be exposed through a public proxy.

## Cost review · checked 17 October 2026

Render is a **candidate**, not a selected/provisioned deployment. Official prices currently list services/workers at USD 7/month for 0.5 CPU/512MB, and basic PostgreSQL at USD 6/month for 256MB or USD 19/month for 1GB. That makes a small API + worker + basic database approximately **USD 20/month**, or **USD 33/month** with the 1GB database, before identity hosting, extra storage, egress, taxes or any separate web proxy/service. A separate paid proxy would add another service. These are planning estimates; performance and account eligibility are not verified.

Storage pricing is separately metered: persistent disks USD 0.25/GB-month and PostgreSQL expansion USD 0.30/GB-month. Check whether a Canadian region, managed role permissions and OIDC hosting fit the chosen plan before selecting it. Prices are USD; no fixed CAD conversion is assumed. The Bank of Canada fixture is indicative data, not a hosting-bill exchange guarantee.

Free web hosting does not automatically include a permanent durable database or continuous worker. Render's free PostgreSQL expires after 30 days; do not present it as a lasting no-cost bank. Reference: [pricing](https://render.com/pricing), [compute plans](https://render.com/docs/compute-plans), [free-plan restrictions](https://render.com/docs/free), [service types](https://render.com/docs/service-types).

Likely larger-profile drivers: Spark executor RAM/CPU, persistent Kafka retention and replication, object storage/history, Airflow services, trace/log retention, backups and egress. Azure/Databricks stays a later profile; no paid workspace is created by this release.

## Local shutdown and retention

`docker compose down` stops the local core and keeps the persistent named volume. Local resource cost is the host/Docker VM, disk and electricity; cloud bill is zero because none is provisioned. A future cloud shutdown must stop/delete billable API/worker/identity services and separately decide whether to retain database, object storage, snapshots and disks. Stopping web traffic alone is not a cost shutdown.

Keep source history within scenario record quotas, CI evidence for 14 days and backups under an explicit operator policy. Hosted off-host retention, timed restore and cryptographic audit/archive requirements remain open. No universal high-availability or disaster-recovery claim follows from one persistent host.
