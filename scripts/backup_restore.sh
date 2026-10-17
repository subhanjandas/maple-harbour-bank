#!/usr/bin/env bash
# Core development drill only. Never restores over the live database.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .runtime/backups
backup_file=".runtime/backups/mhb-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose exec -T db pg_dump -U postgres -d mhb -Fc > "$backup_file"
docker compose exec -T db createdb -U postgres mhb_restore_check
cleanup_restore() { docker compose exec -T db dropdb -U postgres --if-exists mhb_restore_check; }
trap cleanup_restore EXIT
docker compose exec -T db pg_restore -U postgres --no-owner --exit-on-error -d mhb_restore_check < "$backup_file"
live_count=$(docker compose exec -T db psql -U postgres -d mhb -Atc 'SELECT count(*) FROM journal_lines')
restored_count=$(docker compose exec -T db psql -U postgres -d mhb_restore_check -Atc 'SELECT count(*) FROM journal_lines')
test "$live_count" = "$restored_count"
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d mhb_restore_check <<'SQL'
DO $$ BEGIN
 IF EXISTS(SELECT j.id FROM journals j LEFT JOIN journal_lines l ON l.journal_id=j.id GROUP BY j.id HAVING count(l.*)<2 OR coalesce(sum(CASE WHEN direction='DEBIT' THEN amount_minor ELSE -amount_minor END),0)<>0) THEN RAISE EXCEPTION 'RESTORE_JOURNAL_MISMATCH'; END IF;
 IF EXISTS(SELECT a.id FROM accounts a LEFT JOIN journal_lines l ON l.ledger_id=a.ledger_id GROUP BY a.id HAVING a.booked_minor<>coalesce(sum(CASE WHEN direction='CREDIT' THEN amount_minor ELSE -amount_minor END),0)) THEN RAISE EXCEPTION 'RESTORE_ACCOUNT_MISMATCH'; END IF;
END $$;
SQL
printf 'Restored independent database, compared ledger counts and rechecked financial invariants. Backup: %s\n' "$backup_file"
