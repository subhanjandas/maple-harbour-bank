"""Create distinct login credentials after migrations. Passwords never enter shell arguments."""
import os
import psycopg
from psycopg import sql
with psycopg.connect(os.environ['MIGRATION_DATABASE_URL']) as db:
    for login,role,variable in [('mhb_api_login','mhb_api','API_PASSWORD'),('mhb_worker_login','mhb_worker','WORKER_PASSWORD')]:
        if not db.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(login,)).fetchone():
            db.execute(sql.SQL('CREATE ROLE {} LOGIN INHERIT PASSWORD {}').format(sql.Identifier(login),sql.Literal(os.environ[variable])))
        db.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier(role),sql.Identifier(login)))
