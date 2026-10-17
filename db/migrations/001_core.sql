-- Forward-only bootstrap. Service roles cannot migrate or bypass row policies.
DO $$ BEGIN
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='mhb_api') THEN CREATE ROLE mhb_api NOLOGIN; END IF;
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='mhb_worker') THEN CREATE ROLE mhb_worker NOLOGIN; END IF;
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE TABLE tenants (id text PRIMARY KEY, name text NOT NULL);
CREATE TABLE principals (
 id text PRIMARY KEY, tenant_id text NOT NULL REFERENCES tenants, name text NOT NULL,
 role text NOT NULL CHECK(role IN ('customer','operations','analyst','engineer')),
 scope text NOT NULL DEFAULT 'TORONTO', issuer text, subject text, active boolean NOT NULL DEFAULT true,
 UNIQUE(tenant_id,id), UNIQUE(issuer,subject)
);
CREATE TABLE sessions (
 token_hash text PRIMARY KEY, principal_id text NOT NULL REFERENCES principals,
 csrf_hash text NOT NULL, expires_at timestamptz NOT NULL, revoked_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE rate_windows (bucket text PRIMARY KEY, window_at timestamptz NOT NULL, hits integer NOT NULL);
CREATE TABLE ledger_accounts (
 id text PRIMARY KEY, tenant_id text NOT NULL REFERENCES tenants,
 kind text NOT NULL CHECK(kind IN ('ASSET','LIABILITY','EQUITY')), label text NOT NULL,
 UNIQUE(tenant_id,id)
);
CREATE TABLE accounts (
 id text PRIMARY KEY, tenant_id text NOT NULL, owner_id text NOT NULL,
 ledger_id text NOT NULL UNIQUE, label text NOT NULL, currency text NOT NULL DEFAULT 'CAD' CHECK(currency='CAD'),
 currency_exponent smallint NOT NULL DEFAULT 2 CHECK(currency_exponent=2),
 booked_minor bigint NOT NULL DEFAULT 0 CHECK(booked_minor>=0),
 hold_minor bigint NOT NULL DEFAULT 0 CHECK(hold_minor>=0 AND hold_minor<=booked_minor),
 status text NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN','RESTRICTED','CLOSED')),
 scope text NOT NULL DEFAULT 'TORONTO', UNIQUE(tenant_id,id),
 FOREIGN KEY(tenant_id,owner_id) REFERENCES principals(tenant_id,id),
 FOREIGN KEY(tenant_id,ledger_id) REFERENCES ledger_accounts(tenant_id,id)
);
CREATE TABLE beneficiaries (
 id text PRIMARY KEY, tenant_id text NOT NULL, owner_id text NOT NULL, name text NOT NULL,
 UNIQUE(tenant_id,id), FOREIGN KEY(tenant_id,owner_id) REFERENCES principals(tenant_id,id)
);
CREATE TABLE payments (
 id text PRIMARY KEY, tenant_id text NOT NULL, owner_id text NOT NULL, source_id text NOT NULL,
 destination_id text, beneficiary_id text, kind text NOT NULL CHECK(kind IN ('OUTBOUND','INTERNAL')),
 amount_minor bigint NOT NULL CHECK(amount_minor BETWEEN 1 AND 100000000),
 currency text NOT NULL CHECK(currency='CAD'), business_date date NOT NULL,
 status text NOT NULL CHECK(status IN ('POSTED','SETTLED','PARTIALLY_RETURNED','RETURNED','REVERSED')),
 version integer NOT NULL CHECK(version>0), returned_minor bigint NOT NULL DEFAULT 0,
 correlation_id uuid NOT NULL, scope text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 CHECK(returned_minor BETWEEN 0 AND amount_minor),
 CHECK((kind='OUTBOUND' AND beneficiary_id IS NOT NULL AND destination_id IS NULL) OR
       (kind='INTERNAL' AND destination_id IS NOT NULL AND beneficiary_id IS NULL AND destination_id<>source_id)),
 UNIQUE(tenant_id,id), FOREIGN KEY(tenant_id,owner_id) REFERENCES principals(tenant_id,id),
 FOREIGN KEY(tenant_id,source_id) REFERENCES accounts(tenant_id,id),
 FOREIGN KEY(tenant_id,destination_id) REFERENCES accounts(tenant_id,id),
 FOREIGN KEY(tenant_id,beneficiary_id) REFERENCES beneficiaries(tenant_id,id)
);
CREATE INDEX payment_tenant_created ON payments(tenant_id,created_at DESC);
CREATE TABLE payment_events (
 id uuid PRIMARY KEY, tenant_id text NOT NULL, payment_id text NOT NULL,
 version integer NOT NULL, status text NOT NULL, occurred_at timestamptz NOT NULL DEFAULT now(),
 actor_id text NOT NULL REFERENCES principals, reason text NOT NULL,
 UNIQUE(tenant_id,payment_id,version), FOREIGN KEY(tenant_id,payment_id) REFERENCES payments(tenant_id,id)
);
CREATE TABLE returns (
 id text PRIMARY KEY, tenant_id text NOT NULL, payment_id text NOT NULL,
 amount_minor bigint NOT NULL CHECK(amount_minor>0), booked_date date NOT NULL,
 reporting_date date NOT NULL, revision integer NOT NULL DEFAULT 1,
 UNIQUE(tenant_id,id), FOREIGN KEY(tenant_id,payment_id) REFERENCES payments(tenant_id,id)
);
CREATE TABLE journals (
 id uuid PRIMARY KEY, tenant_id text NOT NULL REFERENCES tenants, payment_id text,
 kind text NOT NULL CHECK(kind IN ('OPENING','PAYMENT','SETTLEMENT','RETURN','REVERSAL')),
 currency text NOT NULL CHECK(currency='CAD'), booked_date date NOT NULL,
 correlation_id uuid NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), creation_xid xid8 NOT NULL DEFAULT pg_current_xact_id(),
 UNIQUE(tenant_id,id), FOREIGN KEY(tenant_id,payment_id) REFERENCES payments(tenant_id,id)
);
CREATE TABLE journal_lines (
 journal_id uuid NOT NULL, tenant_id text NOT NULL, line_no smallint NOT NULL,
 ledger_id text NOT NULL, direction text NOT NULL CHECK(direction IN ('DEBIT','CREDIT')),
 amount_minor bigint NOT NULL CHECK(amount_minor>0), PRIMARY KEY(journal_id,line_no),
 FOREIGN KEY(tenant_id,journal_id) REFERENCES journals(tenant_id,id),
 FOREIGN KEY(tenant_id,ledger_id) REFERENCES ledger_accounts(tenant_id,id)
);
CREATE INDEX journal_ledger ON journal_lines(tenant_id,ledger_id);
CREATE TABLE commands (
 tenant_id text NOT NULL, actor_id text NOT NULL REFERENCES principals, key text NOT NULL,
 request_hash text NOT NULL, response jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant_id,actor_id,key)
);
CREATE TABLE outbox (
 seq bigserial PRIMARY KEY, event_id uuid NOT NULL UNIQUE, tenant_id text NOT NULL REFERENCES tenants,
 aggregate_id text NOT NULL, aggregate_version integer NOT NULL, envelope jsonb NOT NULL,
 checksum text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 acknowledged_at timestamptz, attempts integer NOT NULL DEFAULT 0,
 retry_at timestamptz NOT NULL DEFAULT now(), last_error text,
 UNIQUE(tenant_id,aggregate_id,aggregate_version)
);
CREATE INDEX outbox_pending ON outbox(retry_at,seq) WHERE acknowledged_at IS NULL;
CREATE TABLE audit (
 id bigserial PRIMARY KEY, tenant_id text NOT NULL, actor_id text NOT NULL REFERENCES principals,
 action text NOT NULL, resource_id text NOT NULL, correlation_id uuid NOT NULL,
 occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE bronze (
 event_id uuid PRIMARY KEY, tenant_id text NOT NULL, source_seq bigint NOT NULL UNIQUE,
 checksum text NOT NULL, envelope jsonb NOT NULL, received_at timestamptz NOT NULL DEFAULT now(),
 ingestion_run_id uuid NOT NULL
);
CREATE TABLE silver_history (
 event_id uuid PRIMARY KEY REFERENCES bronze, tenant_id text NOT NULL, aggregate_id text NOT NULL,
 aggregate_version integer NOT NULL, checksum text NOT NULL, envelope jsonb NOT NULL,
 UNIQUE(tenant_id,aggregate_id,aggregate_version)
);
CREATE TABLE silver_current (
 tenant_id text NOT NULL, aggregate_id text NOT NULL, version integer NOT NULL, payload jsonb NOT NULL,
 event_id uuid NOT NULL REFERENCES silver_history, PRIMARY KEY(tenant_id,aggregate_id)
);
CREATE TABLE pipeline_runs (
 id uuid PRIMARY KEY, tenant_id text NOT NULL, status text NOT NULL CHECK(status IN ('SUCCEEDED','REJECTED')),
 cutoff bigint NOT NULL, source_count integer NOT NULL, source_checksum text NOT NULL,
 codes jsonb NOT NULL DEFAULT '[]', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE quarantine (
 id bigserial PRIMARY KEY, tenant_id text NOT NULL, run_id uuid NOT NULL REFERENCES pipeline_runs,
 event_id uuid, code text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE publications (
 id uuid PRIMARY KEY, tenant_id text NOT NULL, run_id uuid NOT NULL REFERENCES pipeline_runs,
 cutoff bigint NOT NULL, source_count integer NOT NULL, source_checksum text NOT NULL,
 source_cutoff_at timestamptz, refreshed_at timestamptz NOT NULL DEFAULT now(),
 daily jsonb NOT NULL, totals jsonb NOT NULL, UNIQUE(tenant_id,id)
);
CREATE TABLE serving_pointer (
 tenant_id text PRIMARY KEY REFERENCES tenants, publication_id uuid NOT NULL,
 FOREIGN KEY(tenant_id,publication_id) REFERENCES publications(tenant_id,id)
);

CREATE FUNCTION immutable_record() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'APPEND_ONLY: use a compensating record'; END $$;
CREATE TRIGGER journals_immutable BEFORE UPDATE OR DELETE ON journals FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TRIGGER lines_immutable BEFORE UPDATE OR DELETE ON journal_lines FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TRIGGER events_immutable BEFORE UPDATE OR DELETE ON payment_events FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE ON audit FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TRIGGER bronze_immutable BEFORE UPDATE OR DELETE ON bronze FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TRIGGER history_immutable BEFORE UPDATE OR DELETE ON silver_history FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TRIGGER publication_immutable BEFORE UPDATE OR DELETE ON publications FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE FUNCTION balanced_journal() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE j uuid; n bigint; difference numeric;
BEGIN
 j := CASE WHEN TG_TABLE_NAME='journals' THEN NEW.id ELSE NEW.journal_id END;
 SELECT count(*),coalesce(sum(CASE WHEN direction='DEBIT' THEN amount_minor ELSE -amount_minor END),0)
 INTO n,difference FROM journal_lines WHERE journal_id=j;
 IF n<2 OR difference<>0 THEN RAISE EXCEPTION 'UNBALANCED_JOURNAL'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER journal_balance AFTER INSERT ON journals DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION balanced_journal();
CREATE CONSTRAINT TRIGGER line_balance AFTER INSERT ON journal_lines DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION balanced_journal();
CREATE FUNCTION account_reconciles() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE lid text; expected numeric; actual bigint;
BEGIN
 lid := CASE WHEN TG_TABLE_NAME='accounts' THEN NEW.ledger_id ELSE NEW.ledger_id END;
 SELECT booked_minor INTO actual FROM accounts WHERE ledger_id=lid;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT coalesce(sum(CASE WHEN direction='CREDIT' THEN amount_minor ELSE -amount_minor END),0) INTO expected FROM journal_lines WHERE ledger_id=lid;
 IF actual<>expected THEN RAISE EXCEPTION 'ACCOUNT_LEDGER_MISMATCH'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER account_rollforward AFTER INSERT OR UPDATE ON accounts DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION account_reconciles();
CREATE CONSTRAINT TRIGGER line_rollforward AFTER INSERT ON journal_lines DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION account_reconciles();

-- Fail closed if a service forgets to bind its trusted tenant for a transaction.
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['accounts','beneficiaries','payments','payment_events','returns','journals','journal_lines','commands','audit'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY tenant_api ON %I TO mhb_api USING (tenant_id=current_setting(''mhb.tenant'',true)) WITH CHECK (tenant_id=current_setting(''mhb.tenant'',true))',t);
 END LOOP;
END $$;
GRANT USAGE ON SCHEMA public TO mhb_api,mhb_worker;
GRANT SELECT ON tenants,principals,sessions,accounts,beneficiaries,payments,payment_events,returns,journals,journal_lines,commands,outbox,audit,publications,serving_pointer,pipeline_runs,quarantine TO mhb_api;
GRANT INSERT ON sessions,commands,payments,payment_events,returns,journals,journal_lines,outbox,audit TO mhb_api;
GRANT UPDATE(booked_minor) ON accounts TO mhb_api;
GRANT UPDATE(status,version,returned_minor) ON payments TO mhb_api;
GRANT UPDATE(reporting_date,revision) ON returns TO mhb_api;
GRANT UPDATE(revoked_at) ON sessions TO mhb_api;
GRANT SELECT,INSERT,UPDATE ON rate_windows TO mhb_api;
GRANT USAGE ON SEQUENCE outbox_seq_seq,audit_id_seq TO mhb_api;
GRANT SELECT ON tenants,outbox,bronze,silver_history,silver_current,pipeline_runs,quarantine,publications,serving_pointer TO mhb_worker;
GRANT INSERT ON bronze,silver_history,silver_current,pipeline_runs,quarantine,publications,serving_pointer TO mhb_worker;
GRANT UPDATE ON silver_current,serving_pointer TO mhb_worker;
GRANT UPDATE(acknowledged_at,attempts,retry_at,last_error) ON outbox TO mhb_worker;
GRANT USAGE ON SEQUENCE quarantine_id_seq TO mhb_worker;
REVOKE ALL ON FUNCTION immutable_record(),balanced_journal(),account_reconciles() FROM PUBLIC;
CREATE VIEW event_lineage WITH (security_barrier=true) AS
 SELECT b.tenant_id,b.event_id,b.source_seq,b.received_at,b.ingestion_run_id,
 h.event_id IS NOT NULL AS silver_validated
 FROM bronze b LEFT JOIN silver_history h USING(event_id);
GRANT SELECT ON event_lineage,schema_migrations TO mhb_api;

CREATE FUNCTION journal_accepts_lines() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM journals WHERE id=NEW.journal_id AND creation_xid=pg_current_xact_id()) THEN
  RAISE EXCEPTION 'POSTED_JOURNAL_CLOSED';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER closed_journal BEFORE INSERT ON journal_lines FOR EACH ROW EXECUTE FUNCTION journal_accepts_lines();
REVOKE ALL ON FUNCTION journal_accepts_lines() FROM PUBLIC;
