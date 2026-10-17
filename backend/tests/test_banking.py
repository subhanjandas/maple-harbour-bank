from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import os
import subprocess
import sys
import pytest
import psycopg
from psycopg.types.json import Jsonb
from fastapi import HTTPException
from mhb.domain import PaymentCommand,create_payment,operate,correct_return,digest
from mhb.pipeline import archive_one,cycle,publish,backfill
from mhb.migrate import migrate
from conftest import login


def command(**kw):return PaymentCommand(source_id='harbour:chequing',beneficiary_id='harbour:energy',amount_minor=12500,**kw)
def payment(dbs,actor,key='request-0001',cmd=None):return create_payment(dbs[0],actor,key,cmd or command())['payment_id']
def scalar(admin,sql,args=None):return next(iter(admin.execute(sql,args).fetchone().values()))


def test_health_and_seed_idempotency(client,admin,urls):
    assert client.get('/api/health/live').json()['simulation']
    assert client.get('/api/health/ready').status_code==200
    from mhb.seed import seed
    seed(urls['admin']);migrate(urls['admin'])
    assert scalar(admin,"SELECT booked_minor FROM accounts WHERE id='harbour:chequing'")==500000
    assert scalar(admin,'SELECT count(*) FROM journals')==6


def test_ownership_and_customer_cannot_see_other_account(client,actor,dbs):
    login(client,'sam')
    accounts=client.get('/api/accounts').json();assert len(accounts)==1 and accounts[0]['id']=='harbour:sam'
    pid=payment(dbs,actor)
    assert client.get('/api/payments/'+pid).status_code==404
    response=client.post('/api/payments',json=command().model_dump(),headers={'Idempotency-Key':'sam-attack-01'})
    assert response.status_code==404
    assert client.get('/api/engineering').status_code==403
    assert client.get('/api/analytics').status_code==403
    assert client.post('/api/operations/payments/'+pid+'/settle',headers={'Idempotency-Key':'sam-attack-02'}).status_code==403


def test_expired_revoked_and_csrf_sessions(client,admin):
    login(client)
    assert client.post('/api/auth/logout',headers={'X-CSRF-Token':'forged'}).status_code==403
    assert client.post('/api/auth/logout',headers={'Origin':'https://attacker.example'}).status_code==403
    token=client.cookies['mhb_session'];assert client.post('/api/auth/logout').status_code==200
    client.cookies.set('mhb_session',token)
    assert client.get('/api/me').status_code==401
    login(client);admin.execute("UPDATE sessions SET expires_at=now()-interval '1 second'")
    assert client.get('/api/accounts').status_code==401


def test_payment_posting_is_atomic_and_idempotent(client,admin):
    login(client);headers={'Idempotency-Key':'web-request-001'};body=command().model_dump()
    a=client.post('/api/payments',json=body,headers=headers);assert a.status_code==201,a.text
    b=client.post('/api/payments',json=body,headers=headers);assert a.json()==b.json()
    body['amount_minor']=100
    assert client.post('/api/payments',json=body,headers=headers).status_code==409
    assert scalar(admin,'SELECT count(*) FROM payments')==1
    assert scalar(admin,'SELECT count(*) FROM outbox')==3
    assert scalar(admin,"SELECT booked_minor FROM accounts WHERE id='harbour:chequing'")==487500
    assert scalar(admin,"SELECT count(*) FROM journal_lines WHERE journal_id IN (SELECT id FROM journals WHERE kind='PAYMENT')")==2


@pytest.mark.parametrize('amount',[0,-1,1.1,'12',True,100000001])
def test_exact_money_input_rejected(client,amount):
    login(client);body=command().model_dump();body['amount_minor']=amount
    assert client.post('/api/payments',json=body,headers={'Idempotency-Key':'invalid-money-01'}).status_code==422


def test_duplicate_storm_creates_one_effect(dbs,actor,admin):
    with ThreadPoolExecutor(max_workers=12) as pool:
        replies=list(pool.map(lambda _:create_payment(dbs[0],actor,'duplicate-storm',command()),range(40)))
    assert len({r['payment_id'] for r in replies})==1
    assert scalar(admin,'SELECT count(*) FROM payments')==1
    assert scalar(admin,'SELECT count(*) FROM outbox')==3


def test_hot_account_cannot_overspend(dbs,actor,admin):
    cmd=PaymentCommand(source_id='harbour:chequing',beneficiary_id='harbour:energy',amount_minor=30000)
    def attempt(i):
        try:create_payment(dbs[0],actor,'hot-account-'+str(i),cmd);return True
        except HTTPException as e:assert e.detail=='INSUFFICIENT_AVAILABLE_FUNDS';return False
    with ThreadPoolExecutor(max_workers=12) as pool:results=list(pool.map(attempt,range(30)))
    assert sum(results)==16
    assert scalar(admin,"SELECT booked_minor FROM accounts WHERE id='harbour:chequing'")==20000
    assert scalar(admin,'SELECT count(*) FROM payments')==16


def test_insufficient_funds_leaves_no_partial_state(dbs,actor,admin):
    with pytest.raises(HTTPException,match='INSUFFICIENT'):
        payment(dbs,actor,cmd=PaymentCommand(source_id='harbour:chequing',beneficiary_id='harbour:energy',amount_minor=500001))
    assert scalar(admin,'SELECT count(*) FROM outbox')==0
    assert scalar(admin,'SELECT count(*) FROM payments')==0


def test_internal_transfer_and_compensating_reversal(dbs,actor,ops,admin):
    pid=payment(dbs,actor,cmd=PaymentCommand(source_id='harbour:chequing',kind='INTERNAL',destination_id='harbour:savings',amount_minor=10000))
    assert scalar(admin,"SELECT booked_minor FROM accounts WHERE id='harbour:savings'")==1260000
    operate(dbs[0],ops,pid,'reverse-request-01','reverse')
    assert scalar(admin,"SELECT booked_minor FROM accounts WHERE id='harbour:savings'")==1250000
    assert scalar(admin,"SELECT booked_minor FROM accounts WHERE id='harbour:chequing'")==500000
    assert scalar(admin,"SELECT count(*) FROM journals WHERE payment_id=%s",(pid,))==2
    with pytest.raises(HTTPException,match='INVALID_TRANSITION'):operate(dbs[0],ops,pid,'reverse-request-02','reverse')


def test_scope_and_organization_isolation(dbs,actor,ops,admin,client):
    pid=payment(dbs,actor)
    west=admin.execute("SELECT * FROM principals WHERE id='harbour:ops-west'").fetchone()
    foreign=admin.execute("SELECT * FROM principals WHERE id='other:ops'").fetchone()
    for principal in [west,foreign]:
        with pytest.raises(HTTPException,match='PAYMENT_NOT_FOUND'):operate(dbs[0],principal,pid,'not-my-scope-01','settle')
    login(client,'ops-west');assert client.get('/api/payments').json()==[]
    assert client.get('/api/payments/'+pid).status_code==404


def test_partial_return_limits_and_duplicate_effect(dbs,actor,ops,admin):
    pid=payment(dbs,actor)
    with pytest.raises(HTTPException,match='INVALID_TRANSITION'):operate(dbs[0],ops,pid,'too-early-return','return',{'amount_minor':3000})
    operate(dbs[0],ops,pid,'settlement-001','settle')
    a=operate(dbs[0],ops,pid,'return-0001','return',{'amount_minor':3000})
    assert a==operate(dbs[0],ops,pid,'return-0001','return',{'amount_minor':3000})
    assert a['status']=='PARTIALLY_RETURNED'
    with pytest.raises(HTTPException,match='RETURN_EXCEEDS'):operate(dbs[0],ops,pid,'return-too-big','return',{'amount_minor':10000})
    assert scalar(admin,"SELECT booked_minor FROM accounts WHERE id='harbour:chequing'")==490500
    assert scalar(admin,'SELECT count(*) FROM returns')==1
    operate(dbs[0],ops,pid,'return-final','return',{'amount_minor':9500})
    assert scalar(admin,"SELECT status FROM payments WHERE id=%s",(pid,))=='RETURNED'


def test_database_ledger_immutability_and_balance_constraints(dbs,actor,admin):
    pid=payment(dbs,actor)
    with pytest.raises(psycopg.Error,match='APPEND_ONLY'):admin.execute("UPDATE journal_lines SET amount_minor=1")
    with pytest.raises(psycopg.Error,match='APPEND_ONLY'):admin.execute('DELETE FROM journals')
    with pytest.raises(psycopg.Error,match='ACCOUNT_LEDGER_MISMATCH'):
        with admin.transaction():admin.execute("UPDATE accounts SET booked_minor=1 WHERE id='harbour:chequing'")
    from mhb.domain import post,identifier
    j=admin.execute('SELECT id FROM journals WHERE payment_id=%s',(pid,)).fetchone()['id']
    with pytest.raises(psycopg.Error,match='POSTED_JOURNAL_CLOSED'):
        admin.execute("INSERT INTO journal_lines VALUES (%s,'harbour',3,'harbour:chequing','DEBIT',1)",(j,))
    with pytest.raises(psycopg.Error,match='UNBALANCED_JOURNAL'):
        with admin.transaction():
            admin.execute("INSERT INTO journals(id,tenant_id,kind,currency,booked_date,correlation_id) VALUES (%s,'harbour','PAYMENT','CAD',current_date,%s)",(identifier(),identifier()))


def test_actual_service_roles_deny_raw_and_cross_tenant(dbs,actor,urls):
    with dbs[0].transaction() as db: assert db.execute('SELECT * FROM accounts').fetchall()==[]
    with dbs[0].transaction('harbour') as db: assert all(a['tenant_id']=='harbour' for a in db.execute('SELECT * FROM accounts'))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with dbs[0].transaction() as db:db.execute('SELECT * FROM bronze')
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with dbs[1].transaction() as db:db.execute('SELECT * FROM accounts')
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with dbs[0].transaction() as db:db.execute('TRUNCATE journal_lines')


def test_end_to_end_source_to_publication_and_trace(dbs,actor,ops,client,admin):
    pid=payment(dbs,actor);operate(dbs[0],ops,pid,'settle-001','settle');operate(dbs[0],ops,pid,'return-001','return',{'amount_minor':3000})
    result=cycle(dbs[1]);assert all(x['status']=='SUCCEEDED' for x in result['publications'])
    login(client,'analyst');a=client.get('/api/analytics').json();p=a['publication']
    assert p['totals']['instruction_count']==1
    assert p['totals']['instruction_minor']==12500
    assert p['totals']['return_minor']==3000
    assert p['source_count']==5
    assert p['totals']['reconciled']
    login(client);trace=client.get('/api/payments/'+pid).json()
    assert len(trace['lineage'])==5 and all(r['publication_id'] and r['silver_validated'] for r in trace['lineage'])
    assert client.get('/api/engineering').status_code==403


def test_crash_after_sink_commit_before_ack_recovers(dbs,actor,urls,admin):
    payment(dbs,actor)
    script='import os;from mhb.db import Database;from mhb.pipeline import archive_one;d=Database(os.environ["WORKER_DATABASE_URL"]);d.pool.open(wait=True);archive_one(d,failpoint=lambda:os._exit(17))'
    env={**os.environ,'WORKER_DATABASE_URL':urls['worker']}
    proc=subprocess.run([sys.executable,'-c',script],env=env)
    assert proc.returncode==17
    assert scalar(admin,'SELECT count(*) FROM bronze')==1
    assert scalar(admin,'SELECT count(*) FROM outbox WHERE acknowledged_at IS NOT NULL')==0
    cycle(dbs[1]);assert scalar(admin,'SELECT count(*) FROM bronze')==3
    assert scalar(admin,'SELECT count(*) FROM outbox WHERE acknowledged_at IS NOT NULL')==3
    assert scalar(admin,'SELECT max(attempts) FROM outbox')==2


def test_missing_source_preserves_last_good(dbs,actor,admin):
    payment(dbs,actor);cycle(dbs[1])
    before=scalar(admin,"SELECT publication_id FROM serving_pointer WHERE tenant_id='harbour'")
    payment(dbs,actor,'second-payment-01');archive_one(dbs[1])
    rejected=publish(dbs[1],'harbour');assert rejected['code']=='MISSING_OR_CHANGED_SOURCE'
    assert scalar(admin,"SELECT publication_id FROM serving_pointer WHERE tenant_id='harbour'")==before
    cycle(dbs[1]);assert scalar(admin,"SELECT publication_id FROM serving_pointer WHERE tenant_id='harbour'")!=before


def test_crash_inside_publication_rolls_back(dbs,actor,urls,admin):
    payment(dbs,actor);cycle(dbs[1]);before=scalar(admin,"SELECT publication_id FROM serving_pointer WHERE tenant_id='harbour'")
    script='import os;from mhb.db import Database;from mhb.pipeline import publish;d=Database(os.environ["WORKER_DATABASE_URL"]);d.pool.open(wait=True);publish(d,"harbour",force=True,failpoint=lambda:os._exit(19))'
    proc=subprocess.run([sys.executable,'-c',script],env={**os.environ,'WORKER_DATABASE_URL':urls['worker']})
    assert proc.returncode==19
    assert scalar(admin,"SELECT publication_id FROM serving_pointer WHERE tenant_id='harbour'")==before
    assert publish(dbs[1],'harbour',force=True)['status']=='SUCCEEDED'


def test_late_reporting_correction_changes_period_without_cash(dbs,actor,ops,admin,monkeypatch):
    import mhb.domain as domain
    now=datetime.now(timezone.utc)-timedelta(days=7)
    monkeypatch.setattr(domain,'utcnow',lambda:now);pid=payment(dbs,actor)
    operate(dbs[0],ops,pid,'settlement-001','settle')
    now+=timedelta(days=3)
    operate(dbs[0],ops,pid,'partial-return-1','return',{'amount_minor':3000});cycle(dbs[1])
    rid=scalar(admin,'SELECT id FROM returns');before=scalar(admin,"SELECT booked_minor FROM accounts WHERE id='harbour:chequing'")
    earlier=(now-timedelta(days=1)).astimezone(domain.TORONTO).date();now+=timedelta(days=3)
    correct_return(dbs[0],ops,pid,rid,'late-date-fix-001',earlier);cycle(dbs[1])
    pub=admin.execute("SELECT p.* FROM publications p JOIN serving_pointer s ON s.publication_id=p.id WHERE s.tenant_id='harbour'").fetchone()
    assert next(d for d in pub['daily'] if d['return_count'])['business_date']==str(earlier)
    assert pub['totals']['instruction_count']==1 and pub['totals']['return_minor']==3000
    assert scalar(admin,"SELECT booked_minor FROM accounts WHERE id='harbour:chequing'")==before
    assert scalar(admin,'SELECT count(*) FROM journals WHERE payment_id=%s',(pid,))==3
    assert scalar(admin,'SELECT count(*) FROM silver_history')==6


def test_out_of_order_archive_and_replay_never_downgrade(dbs,actor,ops,admin):
    pid=payment(dbs,actor);operate(dbs[0],ops,pid,'settlement-001','settle')
    rows=admin.execute('SELECT * FROM outbox ORDER BY seq DESC').fetchall()
    with dbs[1].transaction() as db:
        for r in rows:db.execute('INSERT INTO bronze(event_id,tenant_id,source_seq,checksum,envelope,ingestion_run_id) VALUES (%s,%s,%s,%s,%s,%s)',(r['event_id'],r['tenant_id'],r['seq'],r['checksum'],Jsonb(r['envelope']),str(uuid4())))
    assert publish(dbs[1],'harbour')['status']=='SUCCEEDED'
    cycle(dbs[1]);assert scalar(admin,"SELECT version FROM silver_current WHERE aggregate_id=%s",(pid,))==4
    assert scalar(admin,'SELECT count(*) FROM bronze')==4


def test_poison_contract_quarantined_no_publication(dbs,actor,admin):
    payment(dbs,actor);r=admin.execute('SELECT * FROM outbox ORDER BY seq LIMIT 1').fetchone();e=r['envelope'];e['schema_version']=99
    admin.execute('UPDATE outbox SET envelope=%s,checksum=%s WHERE seq=%s',(Jsonb(e),digest(e),r['seq']))
    result=cycle(dbs[1]);assert result['publications'][0]['status']=='REJECTED'
    assert scalar(admin,"SELECT count(*) FROM serving_pointer WHERE tenant_id='harbour'")==0
    assert scalar(admin,"SELECT code FROM quarantine LIMIT 1")=='CONTRACT_V1_REJECTED'


def test_bounded_backfill_and_unauthorized_backfill(client,dbs,actor):
    from datetime import date
    payment(dbs,actor);cycle(dbs[1])
    with pytest.raises(ValueError,match='BACKFILL_LIMIT'):backfill(dbs[1],'harbour',date(2026,1,1),date(2026,12,31))
    login(client)
    assert client.post('/api/engineering/backfill',json={}).status_code==404
    assert client.get('/api/metrics').status_code==403


def test_unknown_future_migration_fails_closed(admin,urls):
    admin.execute("INSERT INTO schema_migrations(version,sha256) VALUES ('999_future.sql','not-known')")
    try:
        with pytest.raises(RuntimeError,match='unknown future'):migrate(urls['admin'])
    finally:admin.execute("DELETE FROM schema_migrations WHERE version='999_future.sql'")


def test_hosted_configuration_fails_closed():
    from mhb.config import Settings
    from mhb.api import create_app
    with pytest.raises(RuntimeError):create_app(Settings(database_url='postgresql://invalid',session_secret='x'*40,environment='production',demo_auth=True))


def test_architecture_manifest_links_are_real(client):
    data=client.get('/api/architecture').json();assert data['components'];ids={n['id'] for n in data['components']}
    assert all(e['from'] in ids and e['to'] in ids for e in data['connections'])
