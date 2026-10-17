"""Checksum-verified forward migrations. Run with the schema owner, never API credentials."""
import hashlib
import os
from pathlib import Path
import psycopg

ROOT = Path(__file__).resolve().parents[2]

def migrate(url=None):
    with psycopg.connect(url or os.environ['MIGRATION_DATABASE_URL']) as db:
        db.execute('SELECT pg_advisory_xact_lock(420010)')
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())')
        files=sorted((ROOT/'db/migrations').glob('*.sql'))
        applied=dict(db.execute('SELECT version,sha256 FROM schema_migrations').fetchall())
        if set(applied)-{p.name for p in files}: raise RuntimeError('Database has unknown future migrations')
        for p in files:
            checksum=hashlib.sha256(p.read_bytes()).hexdigest()
            if p.name in applied:
                if applied[p.name]!=checksum: raise RuntimeError(f'Modified applied migration: {p.name}')
                continue
            db.execute(p.read_text())
            db.execute('INSERT INTO schema_migrations(version,sha256) VALUES (%s,%s)',(p.name,checksum))
            print(f'Applied {p.name} {checksum}')

if __name__=='__main__': migrate()
