-- Defense in depth: approved analytical data is still tenant-scoped.
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['publications','serving_pointer','pipeline_runs','quarantine'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY serving_api_tenant ON %I TO mhb_api USING (tenant_id=current_setting(''mhb.tenant'',true))',t);
  EXECUTE format('CREATE POLICY serving_worker ON %I TO mhb_worker USING (true) WITH CHECK (true)',t);
 END LOOP;
END $$;
-- The owner-backed metadata view intentionally grants no raw-table access.
CREATE OR REPLACE VIEW event_lineage WITH (security_barrier=true) AS
 SELECT b.tenant_id,b.event_id,b.source_seq,b.received_at,b.ingestion_run_id,
 h.event_id IS NOT NULL AS silver_validated
 FROM bronze b LEFT JOIN silver_history h USING(event_id)
 WHERE b.tenant_id=current_setting('mhb.tenant',true);
