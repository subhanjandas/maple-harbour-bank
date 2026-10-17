-- The first integration run caught eager record-field resolution in a CASE expression.
-- Separate statements ensure each trigger shape references only fields it actually has.
CREATE OR REPLACE FUNCTION balanced_journal() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE j uuid; n bigint; difference numeric;
BEGIN
 IF TG_TABLE_NAME='journals' THEN j:=NEW.id;
 ELSE j:=NEW.journal_id;
 END IF;
 SELECT count(*),coalesce(sum(CASE WHEN direction='DEBIT' THEN amount_minor ELSE -amount_minor END),0)
 INTO n,difference FROM journal_lines WHERE journal_id=j;
 IF n<2 OR difference<>0 THEN RAISE EXCEPTION 'UNBALANCED_JOURNAL'; END IF;
 RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION account_reconciles() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE expected numeric; actual bigint;
BEGIN
 SELECT booked_minor INTO actual FROM accounts WHERE ledger_id=NEW.ledger_id;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT coalesce(sum(CASE WHEN direction='CREDIT' THEN amount_minor ELSE -amount_minor END),0) INTO expected FROM journal_lines WHERE ledger_id=NEW.ledger_id;
 IF actual<>expected THEN RAISE EXCEPTION 'ACCOUNT_LEDGER_MISMATCH'; END IF;
 RETURN NULL;
END $$;
