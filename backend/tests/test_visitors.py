"""Real-database visitor admission, isolation, expiry and upgrade acceptance."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlencode, urlparse
import secrets

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from mhb.api import create_app
from mhb.config import Settings
from mhb.domain import PaymentCommand, create_payment
from mhb.migrate import migrate
from mhb.pipeline import cycle
from mhb.provision import VisitorRequest, provision, deactivate
from conftest import login
from test_oidc import provider


def request(subject='visitor-001', **changes):
    return VisitorRequest(**dict({'issuer':'https://issuer.example', 'subject':subject,
                                  'display_name':'Synthetic visitor', 'operator_label':'acceptance-test'}, **changes))


def test_subhanjan_display_name_upgrade_preserves_identity_and_money(client, admin, urls):
    login(client, 'subhanjan')
    assert client.get('/api/me').json()['name']=='Subhanjan Das'
    assert client.get('/api/me').json()['id']=='harbour:alex'
    before=admin.execute('SELECT * FROM journal_lines ORDER BY journal_id,line_no').fetchall()
    admin.execute("UPDATE principals SET name='Alex Morgan' WHERE id IN ('harbour:alex','other:alex')")
    admin.execute("DELETE FROM schema_migrations WHERE version='006_customer_name.sql'")
    migrate(urls['admin']);migrate(urls['admin'])
    assert client.get('/api/me').json()['name']=='Subhanjan Das'
    assert admin.execute('SELECT * FROM journal_lines ORDER BY journal_id,line_no').fetchall()==before
    assert client.get('/api/accounts').json()[0]['booked_minor']==500000


def test_concurrent_visitor_admission_never_refunds_or_creates_staff(admin, urls, dbs):
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda _:provision(request(), urls['admin']), range(16)))
    assert sum(r['created'] for r in results)==1
    assert len({r['tenant_id'] for r in results})==1
    result=results[0];tenant=result['tenant_id']
    people=admin.execute('SELECT * FROM principals WHERE tenant_id=%s',(tenant,)).fetchall()
    assert len(people)==1 and people[0]['role']=='customer'
    cmd=PaymentCommand(source_id=tenant+':chequing', beneficiary_id=tenant+':energy', amount_minor=1234)
    create_payment(dbs[0],people[0],'visitor-payment-01',cmd)
    assert not provision(request(),urls['admin'])['created']
    assert admin.execute('SELECT booked_minor FROM accounts WHERE id=%s',(tenant+':chequing',)).fetchone()['booked_minor']==498766
    assert admin.execute("SELECT count(*) n FROM journals WHERE tenant_id=%s AND kind='OPENING'",(tenant,)).fetchone()['n']==2
    assert admin.execute('SELECT count(*) n FROM scenario_admin_events WHERE tenant_id=%s',(tenant,)).fetchone()['n']==1


def test_capacity_is_atomic_and_counts_expired_scenarios(admin, urls):
    admin.execute('UPDATE visitor_capacity SET scenario_limit=1')
    def attempt(subject):
        try:return provision(request(subject),urls['admin'])
        except ValueError as e:assert str(e)=='VISITOR_CAPACITY_REACHED';return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(attempt,['first','second']))
    assert sum(r is not None for r in results)==1
    row=next(r for r in results if r)
    deactivate(row['tenant_id'],'acceptance-test',urls['admin'])
    with pytest.raises(ValueError,match='VISITOR_CAPACITY_REACHED'):provision(request('third'),urls['admin'])
    assert admin.execute('SELECT count(*) n FROM visitor_scenarios').fetchone()['n']==1


def test_provisioning_failure_rolls_back_funding_and_identity(admin, urls, monkeypatch):
    import mhb.provision as module
    original=module.post
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError('injected-after-first-journal')
    monkeypatch.setattr(module,'post',fail)
    with pytest.raises(RuntimeError,match='injected'):provision(request(),urls['admin'])
    assert admin.execute('SELECT count(*) n FROM visitor_scenarios').fetchone()['n']==0
    assert admin.execute('SELECT count(*) n FROM journals').fetchone()['n']==6
    assert admin.execute('SELECT count(*) n FROM tenants').fetchone()['n']==2


def test_no_service_can_provision_or_grant_itself_roles(admin, urls):
    for role in ['api','worker']:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):provision(request(),urls[role])
        with psycopg.connect(urls[role]) as db:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                db.execute("UPDATE principals SET role='engineer' WHERE id='harbour:alex'")
    with pytest.raises(ValidationError):request(role='engineer')
    with pytest.raises(ValidationError):request(event_limit=50001)
    with pytest.raises(ValidationError):request(lifetime_days=31)
    with pytest.raises(ValueError,match='HTTPS_ISSUER_REQUIRED'):provision(request(issuer='http://issuer.example'),urls['admin'])


def oidc_login(client, provider, subject):
    provider['subject']=subject
    start=client.get('/api/auth/login')
    query=parse_qs(urlparse(start.headers['location']).query)
    provider['challenge']=query['code_challenge'][0];provider['nonce']=query['nonce'][0]
    response=client.get('/api/auth/callback?'+urlencode({'code':'test-code','state':query['state'][0]}))
    if response.status_code==303:client.headers['X-CSRF-Token']=client.cookies['mhb_csrf']
    return response


def test_two_oidc_visitors_cannot_cross_accounts_payments_or_staff_workspaces(admin, urls, dbs, provider):
    one=provision(request('one',issuer=provider['issuer'],display_name='Subhanjan Das'),urls['admin'],allow_loopback_test_issuer=True)
    two=provision(request('two',issuer=provider['issuer']),urls['admin'],allow_loopback_test_issuer=True)
    settings=Settings(database_url=urls['api'],session_secret=secrets.token_hex(40),demo_auth=False,oidc_issuer=provider['issuer'])
    with TestClient(create_app(settings),base_url=settings.origin,follow_redirects=False,headers={'Origin':settings.origin}) as a, TestClient(create_app(settings),base_url=settings.origin,follow_redirects=False,headers={'Origin':settings.origin}) as b:
        assert oidc_login(a,provider,'one').status_code==303
        assert oidc_login(b,provider,'two').status_code==303
        assert a.get('/api/me').json()['name']=='Subhanjan Das'
        # Signed provider claims include forged role/tenant hints; DB assignment wins.
        assert a.get('/api/me').json()['role']=='customer'
        assert a.get('/api/me').json()['tenant_id']==one['tenant_id']
        assert all(x['id'].startswith(one['tenant_id']+':') for x in a.get('/api/accounts').json())
        body={'source_id':one['tenant_id']+':chequing','beneficiary_id':one['tenant_id']+':energy','amount_minor':100}
        result=a.post('/api/payments',json=body,headers={'Idempotency-Key':'visitor-http-001'})
        assert result.status_code==201,result.text
        pid=result.json()['payment_id'];cycle(dbs[1])
        assert b.get('/api/payments/'+pid).status_code==404
        assert b.post('/api/payments',json=body,headers={'Idempotency-Key':'cross-visitor-01'}).status_code==404
        assert b.get('/api/payments').json()==[]
        for path in ['/api/analytics','/api/engineering','/api/metrics']:
            assert a.get(path).status_code==403
        assert a.post('/api/auth/development/ops').status_code==404
        assert a.post('/api/visitors',json={}).status_code==404
        before=admin.execute('SELECT count(*) n FROM journals').fetchone()['n']
        assert deactivate(one['tenant_id'],'acceptance-test',urls['admin'])['changed']
        assert not deactivate(one['tenant_id'],'acceptance-test',urls['admin'])['changed']
        assert a.get('/api/accounts').status_code==401
        assert oidc_login(a,provider,'one').status_code==403
        assert b.get('/api/accounts').status_code==200
        assert not provision(request('one',issuer=provider['issuer']),urls['admin'],allow_loopback_test_issuer=True)['created']
        assert admin.execute('SELECT count(*) n FROM journals').fetchone()['n']==before
        assert a.get('/api/accounts').status_code==401
        admin.execute("UPDATE visitor_scenarios SET created_at=now()-interval '2 days',expires_at=now()-interval '1 day' WHERE tenant_id=%s",(two['tenant_id'],))
        assert b.get('/api/accounts').status_code==401
        assert oidc_login(b,provider,'two').status_code==403


def test_analytical_database_policies_and_lineage_fail_closed(dbs, actor, admin):
    create_payment(dbs[0],actor,'rls-payment-001',PaymentCommand(source_id='harbour:chequing',beneficiary_id='harbour:energy',amount_minor=100))
    cycle(dbs[1])
    for table in ['publications','serving_pointer','pipeline_runs','event_lineage']:
        with dbs[0].transaction() as db:
            assert db.execute('SELECT * FROM '+table).fetchall()==[]
        with dbs[0].transaction('other') as db:
            assert all(r['tenant_id']=='other' for r in db.execute('SELECT * FROM '+table))
        with dbs[0].transaction('harbour') as db:
            rows=db.execute('SELECT * FROM '+table).fetchall()
            assert rows and all(r['tenant_id']=='harbour' for r in rows)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with dbs[0].transaction('harbour') as db:db.execute('SELECT * FROM scenario_admin_events')
