-- Bounded local scenarios. Accepted money movement never loses its source event:
-- exhaustion rejects and rolls back the whole command.
CREATE TABLE scenario_limits (
 tenant_id text PRIMARY KEY REFERENCES tenants, event_count bigint NOT NULL DEFAULT 0,
 event_limit bigint NOT NULL DEFAULT 50000 CHECK(event_limit BETWEEN 3 AND 1000000)
);
INSERT INTO scenario_limits(tenant_id,event_count)
 SELECT tenant_id,count(*) FROM outbox GROUP BY tenant_id;
CREATE FUNCTION source_quota() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE allowed bigint;
BEGIN
 INSERT INTO scenario_limits(tenant_id) VALUES (NEW.tenant_id) ON CONFLICT DO NOTHING;
 UPDATE scenario_limits SET event_count=event_count+1
 WHERE tenant_id=NEW.tenant_id AND event_count<event_limit RETURNING event_count INTO allowed;
 IF NOT FOUND THEN RAISE EXCEPTION 'SCENARIO_EVENT_QUOTA_REACHED' USING ERRCODE='54000'; END IF;
 IF octet_length(NEW.envelope::text)>65536 THEN RAISE EXCEPTION 'EVENT_ENVELOPE_LIMIT' USING ERRCODE='54000'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER outbox_bounds BEFORE INSERT ON outbox FOR EACH ROW EXECUTE FUNCTION source_quota();
REVOKE ALL ON FUNCTION source_quota() FROM PUBLIC;
