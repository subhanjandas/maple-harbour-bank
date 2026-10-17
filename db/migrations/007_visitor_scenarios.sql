-- Operator-provisioned customer-only scenarios. No API/worker provisioning permission.
CREATE TABLE visitor_capacity (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 scenario_limit integer NOT NULL DEFAULT 100 CHECK(scenario_limit BETWEEN 1 AND 1000)
);
INSERT INTO visitor_capacity(singleton) VALUES (true);
CREATE TABLE visitor_scenarios (
 tenant_id text PRIMARY KEY REFERENCES tenants,
 principal_id text NOT NULL UNIQUE,
 created_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL CHECK(expires_at>created_at),
 disabled_at timestamptz,
 FOREIGN KEY(tenant_id,principal_id) REFERENCES principals(tenant_id,id)
);
CREATE TABLE scenario_admin_events (
 id uuid PRIMARY KEY, tenant_id text NOT NULL REFERENCES visitor_scenarios,
 action text NOT NULL CHECK(action IN ('PROVISION','DEACTIVATE')),
 operator_label text NOT NULL, occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER scenario_admin_immutable BEFORE UPDATE OR DELETE ON scenario_admin_events
 FOR EACH ROW EXECUTE FUNCTION immutable_record();
-- Authentication can inspect expiry before binding a tenant; no financial data here.
GRANT SELECT ON visitor_scenarios TO mhb_api;
