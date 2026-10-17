import os
import secrets
import pytest
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo, conninfo_to_dict
from psycopg.rows import dict_row
from fastapi.testclient import TestClient
from mhb.migrate import migrate
from mhb.seed import seed
from mhb.db import Database
from mhb.api import create_app
from mhb.config import Settings

ORIGIN='http://localhost:8080'

@pytest.fixture(scope='session')
def urls():
    url=os.environ.get('TEST_DATABASE_URL')
    if not url: pytest.skip('PostgreSQL required. Set TEST_DATABASE_URL; CI supplies real PostgreSQL.')
    migrate(url)
    values={'admin':url}
    with psycopg.connect(url,autocommit=True) as db:
        for role in ['api','worker']:
            login='mhb_test_'+role;password=secrets.token_hex(20)
            if not db.execute('SELECT FROM pg_roles WHERE rolname=%s',(login,)).fetchone():db.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(login)))
            db.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(login),sql.Literal(password)))
            db.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier('mhb_'+role),sql.Identifier(login)))
            conn=conninfo_to_dict(url);conn.update(user=login,password=password);values[role]=make_conninfo(**conn)
    return values

@pytest.fixture
def dbs(urls):
    with psycopg.connect(urls['admin'],autocommit=True) as db:
        tables=[r[0] for r in db.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename<>'schema_migrations'")]
        db.execute(sql.SQL('TRUNCATE {} RESTART IDENTITY CASCADE').format(sql.SQL(',').join(map(sql.Identifier,tables))))
        db.execute('INSERT INTO visitor_capacity(singleton) VALUES (true)')
    seed(urls['admin'])
    api=Database(urls['api']);worker=Database(urls['worker']);api.pool.open(wait=True);worker.pool.open(wait=True)
    try:yield api,worker
    finally:api.pool.close();worker.pool.close()

@pytest.fixture
def admin(urls,dbs):
    with psycopg.connect(urls['admin'],row_factory=dict_row,autocommit=True) as db:yield db

@pytest.fixture
def actor(admin):return admin.execute("SELECT * FROM principals WHERE id='harbour:alex'").fetchone()

@pytest.fixture
def ops(admin):return admin.execute("SELECT * FROM principals WHERE id='harbour:ops'").fetchone()

@pytest.fixture
def client(urls,dbs):
    settings=Settings(database_url=urls['api'],session_secret=secrets.token_hex(40),demo_auth=True,origin=ORIGIN,request_limit=10000)
    with TestClient(create_app(settings),base_url=ORIGIN,headers={'Origin':ORIGIN}) as c:yield c

def login(client,persona='alex'):
    response=client.post('/api/auth/development/'+persona);assert response.status_code==200,response.text
    client.headers['X-CSRF-Token']=client.cookies['mhb_csrf']
    return client
