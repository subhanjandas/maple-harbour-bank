-- API serving only needs event metadata. Source envelopes remain write-only for it.
REVOKE SELECT ON outbox FROM mhb_api;
GRANT SELECT(seq,event_id,tenant_id,aggregate_id,aggregate_version,created_at,acknowledged_at,attempts,retry_at,last_error) ON outbox TO mhb_api;
ALTER TABLE outbox ENABLE ROW LEVEL SECURITY;
CREATE POLICY source_tenant_api ON outbox TO mhb_api
 USING(tenant_id=current_setting('mhb.tenant',true))
 WITH CHECK(tenant_id=current_setting('mhb.tenant',true));
CREATE POLICY source_worker_read ON outbox FOR SELECT TO mhb_worker USING(true);
CREATE POLICY source_worker_ack ON outbox FOR UPDATE TO mhb_worker USING(true) WITH CHECK(true);
