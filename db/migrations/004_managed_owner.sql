-- The schema owner is a trusted migration/constraint principal, not the API login.
-- Ordinary managed-PostgreSQL owners must be able to validate all ledger lines in
-- SECURITY DEFINER constraint functions. FORCE RLS would hide rows from that owner.
-- Services remain non-owners, subject to ENABLE RLS and without ALTER permission.
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['accounts','beneficiaries','payments','payment_events','returns','journals','journal_lines','commands','audit'] LOOP
  EXECUTE format('ALTER TABLE %I NO FORCE ROW LEVEL SECURITY',t);
 END LOOP;
END $$;
