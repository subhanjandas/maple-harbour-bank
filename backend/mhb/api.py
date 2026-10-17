import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Header
from fastapi.responses import JSONResponse, RedirectResponse, PlainTextResponse
from starlette.middleware.sessions import SessionMiddleware
from psycopg.errors import LockNotAvailable, QueryCanceled, ProgramLimitExceeded
from .config import Settings
from .db import Database
from .identity import authenticate, create_session, require, hash_token, COOKIE
from .domain import PaymentCommand, ReturnCommand, CorrectionCommand, create_payment, operate, correct_return, visible_payment

ROOT=Path(__file__).resolve().parents[2]
LOG=logging.getLogger('mhb.api')

def create_app(settings=None):
    settings=settings or Settings(); settings.validate()
    if settings.demo_auth and urlparse(settings.origin).hostname not in {'localhost','127.0.0.1'}:
        raise RuntimeError('Development persona login is only allowed at a loopback origin')
    database=Database(settings.database_url)
    @asynccontextmanager
    async def lifespan(app):
        database.pool.open(wait=True)
        yield
        database.pool.close()
    app=FastAPI(title='Maple Harbour Bank · synthetic banking API',version='0.2.0',lifespan=lifespan,docs_url=None,redoc_url=None)
    app.state.db=database;app.state.settings=settings
    app.add_middleware(SessionMiddleware,secret_key=settings.session_secret,session_cookie='mhb_oidc_flow',max_age=300,same_site='lax',https_only=settings.secure_cookies)
    oauth=OAuth()
    if settings.oidc_issuer:
        oauth.register(name='bank',client_id=settings.oidc_client_id,client_secret=settings.oidc_client_secret or None,
                       server_metadata_url=settings.oidc_issuer.rstrip('/')+'/.well-known/openid-configuration',
                       client_kwargs={'scope':'openid profile','code_challenge_method':'S256','timeout':5})

    @app.middleware('http')
    async def headers(request,call_next):
        started=time.perf_counter();trace=str(uuid4())
        response=await call_next(request)
        response.headers.update({'X-Request-ID':trace,'X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin',
                                 'Cache-Control':'no-store','X-Frame-Options':'DENY'})
        LOG.info(json.dumps({'event':'http.request','request_id':trace,'method':request.method,
                            'route':getattr(request.scope.get('route'),'path','unmatched'),
                            'status':response.status_code,'duration_ms':round((time.perf_counter()-started)*1000,2)}))
        return response

    @app.exception_handler(ProgramLimitExceeded)
    async def bounded_scenario(request,exc):
        return JSONResponse({'detail':'SYNTHETIC_SCENARIO_LIMIT_REACHED'},status_code=409)

    @app.exception_handler(LockNotAvailable)
    @app.exception_handler(QueryCanceled)
    async def contention(request,exc):
        return JSONResponse({'detail':'RETRYABLE_CONTENTION'},status_code=503,headers={'Retry-After':'1'})

    @app.get('/api/health/live')
    def live(): return {'status':'ok','application':'0.2.0','simulation':True}

    @app.get('/api/health/ready')
    def ready():
        try:
            with database.transaction() as db:
                migrations=db.execute('SELECT version FROM schema_migrations ORDER BY version').fetchall()
                if [r['version'] for r in migrations]!=['001_core.sql','002_journal_trigger.sql','003_scenario_bounds.sql','004_managed_owner.sql','005_outbox_access.sql','006_customer_name.sql','007_visitor_scenarios.sql','008_serving_isolation.sql']: raise RuntimeError('migration mismatch')
            return {'status':'ready'}
        except Exception: raise HTTPException(503,'DATABASE_OR_MIGRATION_NOT_READY') from None

    @app.get('/api/auth/config')
    def auth_config(): return {'development_personas':settings.demo_auth,'oidc':bool(settings.oidc_issuer),'environment':settings.environment}

    @app.post('/api/auth/development/{persona}')
    def development_login(persona:str,request:Request,response:Response):
        if not settings.demo_auth or settings.environment!='development': raise HTTPException(404,'NOT_FOUND')
        if request.headers.get('origin')!=settings.origin: raise HTTPException(403,'ORIGIN_DENIED')
        # Preserve the original synthetic principal ID and financial history.
        if persona=='subhanjan': persona='alex'
        if persona not in {'alex','sam','ops','ops-west','analyst','engineer'}: raise HTTPException(404,'PERSONA_NOT_FOUND')
        with database.transaction() as db:
            principal=db.execute('SELECT * FROM principals WHERE id=%s AND active',('harbour:'+persona,)).fetchone()
            rate=db.execute('''INSERT INTO rate_windows VALUES (%s,date_trunc('minute',now()),1) ON CONFLICT(bucket)
              DO UPDATE SET window_at=date_trunc('minute',now()),hits=CASE WHEN rate_windows.window_at=date_trunc('minute',now())
              THEN rate_windows.hits+1 ELSE 1 END RETURNING hits''',('login:'+str(request.client.host),)).fetchone()
        if rate['hits']>30: raise HTTPException(429,'LOGIN_RATE_LIMITED')
        if not principal: raise HTTPException(404,'PERSONA_NOT_SEEDED')
        create_session(database,principal,response,settings.secure_cookies)
        return {'authenticated':True,'mode':'LOCAL_DEVELOPMENT_PERSONA'}

    @app.get('/api/auth/login')
    async def login(request:Request):
        if not settings.oidc_issuer: raise HTTPException(503,'OIDC_NOT_CONFIGURED')
        return await oauth.bank.authorize_redirect(request,settings.origin+'/api/auth/callback')

    @app.get('/api/auth/callback')
    async def callback(request:Request):
        if not settings.oidc_issuer: raise HTTPException(404,'NOT_FOUND')
        try:
            token=await oauth.bank.authorize_access_token(request)
            claims=token['userinfo']
            if claims.get('iss')!=settings.oidc_issuer: raise ValueError('issuer')
        except Exception: raise HTTPException(401,'OIDC_VALIDATION_FAILED') from None
        with database.transaction() as db:
            principal=db.execute('SELECT p.* FROM principals p LEFT JOIN visitor_scenarios v ON v.principal_id=p.id WHERE p.issuer=%s AND p.subject=%s AND p.active AND (v.principal_id IS NULL OR (v.disabled_at IS NULL AND v.expires_at>now()))',(claims['iss'],claims['sub'])).fetchone()
        if not principal: raise HTTPException(403,'IDENTITY_NOT_PROVISIONED')
        response=RedirectResponse(settings.origin,status_code=303)
        create_session(database,principal,response,settings.secure_cookies)
        request.session.clear()
        return response

    @app.get('/api/me')
    def me(actor=Depends(authenticate)):
        return {k:actor[k] for k in ['id','name','role','scope','tenant_id']}

    @app.post('/api/auth/logout')
    def logout(request:Request,response:Response,actor=Depends(authenticate)):
        with database.transaction() as db:
            db.execute('UPDATE sessions SET revoked_at=now() WHERE token_hash=%s',(hash_token(request.cookies[COOKIE]),))
        response.delete_cookie(COOKIE);response.delete_cookie('mhb_csrf')
        return {'revoked':True}

    @app.get('/api/accounts')
    def accounts(actor=Depends(authenticate)):
        require(actor,'customer')
        with database.transaction(actor['tenant_id']) as db:
            return db.execute('SELECT id,label,currency,currency_exponent,booked_minor,hold_minor,booked_minor-hold_minor AS available_minor,status FROM accounts WHERE tenant_id=%s AND owner_id=%s ORDER BY id',(actor['tenant_id'],actor['id'])).fetchall()

    @app.get('/api/beneficiaries')
    def beneficiaries(actor=Depends(authenticate)):
        require(actor,'customer')
        with database.transaction(actor['tenant_id']) as db:
            return db.execute('SELECT id,name FROM beneficiaries WHERE tenant_id=%s AND owner_id=%s ORDER BY id',(actor['tenant_id'],actor['id'])).fetchall()

    @app.post('/api/payments',status_code=201)
    def payment(command:PaymentCommand,actor=Depends(authenticate),idempotency_key:str=Header(...)):
        return create_payment(database,actor,idempotency_key,command)

    @app.get('/api/payments')
    def payments(actor=Depends(authenticate)):
        require(actor,'customer','operations')
        with database.transaction(actor['tenant_id']) as db:
            return db.execute('''SELECT id,kind,source_id,amount_minor,currency,status,returned_minor,version,business_date,created_at,correlation_id
              FROM payments WHERE tenant_id=%s AND ((%s='customer' AND owner_id=%s) OR (%s='operations' AND scope=%s))
              ORDER BY created_at DESC,id LIMIT 100''',(actor['tenant_id'],actor['role'],actor['id'],actor['role'],actor['scope'])).fetchall()

    @app.get('/api/payments/{pid}')
    def detail(pid:str,actor=Depends(authenticate)):
        require(actor,'customer','operations')
        with database.transaction(actor['tenant_id']) as db:
            p=visible_payment(db,actor,pid)
            events=db.execute('SELECT id,version,status,reason,occurred_at FROM payment_events WHERE tenant_id=%s AND payment_id=%s ORDER BY version',(actor['tenant_id'],pid)).fetchall()
            returns=db.execute('SELECT id,amount_minor,booked_date,reporting_date,revision FROM returns WHERE tenant_id=%s AND payment_id=%s ORDER BY booked_date,id',(actor['tenant_id'],pid)).fetchall()
            journals=db.execute('''SELECT j.id,j.kind,j.booked_date,l.line_no,l.ledger_id,l.direction,l.amount_minor FROM journals j
               JOIN journal_lines l ON l.journal_id=j.id WHERE j.tenant_id=%s AND j.payment_id=%s ORDER BY j.created_at,l.line_no''',(actor['tenant_id'],pid)).fetchall()
            lineage=db.execute('''SELECT o.event_id,o.seq,o.aggregate_version,o.acknowledged_at,l.received_at,l.ingestion_run_id,l.silver_validated,
             p.id AS publication_id,p.run_id AS publication_run_id
             FROM outbox o LEFT JOIN event_lineage l ON l.event_id=o.event_id
             LEFT JOIN serving_pointer s ON s.tenant_id=o.tenant_id LEFT JOIN publications p ON p.id=s.publication_id AND p.cutoff>=o.seq
             WHERE o.tenant_id=%s AND o.aggregate_id=%s ORDER BY o.aggregate_version''',(actor['tenant_id'],pid)).fetchall()
            return {'payment':p,'events':events,'returns':returns,'journals':journals,'lineage':lineage}

    @app.post('/api/operations/payments/{pid}/settle')
    def settle(pid:str,actor=Depends(authenticate),idempotency_key:str=Header(...)):
        return operate(database,actor,pid,idempotency_key,'settle')

    @app.post('/api/operations/payments/{pid}/returns')
    def returns(pid:str,command:ReturnCommand,actor=Depends(authenticate),idempotency_key:str=Header(...)):
        return operate(database,actor,pid,idempotency_key,'return',command.model_dump())

    @app.post('/api/operations/payments/{pid}/reverse')
    def reverse(pid:str,actor=Depends(authenticate),idempotency_key:str=Header(...)):
        return operate(database,actor,pid,idempotency_key,'reverse')

    @app.post('/api/operations/payments/{pid}/returns/{rid}/reporting-date')
    def correction(pid:str,rid:str,command:CorrectionCommand,actor=Depends(authenticate),idempotency_key:str=Header(...)):
        return correct_return(database,actor,pid,rid,idempotency_key,command.reporting_date)

    @app.get('/api/analytics')
    def analytics(actor=Depends(authenticate)):
        require(actor,'analyst','engineer','operations')
        with database.transaction(actor['tenant_id']) as db:
            p=db.execute('SELECT p.* FROM serving_pointer s JOIN publications p ON s.publication_id=p.id WHERE s.tenant_id=%s',(actor['tenant_id'],)).fetchone()
            if not p: return {'publication':None,'freshness':'unpublished'}
            lag=(datetime.now(timezone.utc)-p['refreshed_at']).total_seconds()
            newer=db.execute('SELECT count(*) n FROM outbox WHERE tenant_id=%s AND seq>%s',(actor['tenant_id'],p['cutoff'])).fetchone()['n']
            return {'publication':p,'freshness':'current' if newer==0 and 0<=lag<=60 else 'stale','age_seconds':round(lag,1),'unpublished_events':newer}

    @app.get('/api/engineering')
    def engineering(actor=Depends(authenticate)):
        require(actor,'engineer')
        with database.transaction(actor['tenant_id']) as db:
            counts=db.execute('SELECT count(*) total,count(*) FILTER(WHERE acknowledged_at IS NULL) pending,coalesce(max(attempts),0) max_attempts FROM outbox WHERE tenant_id=%s',(actor['tenant_id'],)).fetchone()
            runs=db.execute('SELECT * FROM pipeline_runs WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 30',(actor['tenant_id'],)).fetchall()
            quarantines=db.execute('SELECT code,count(*) n FROM quarantine WHERE tenant_id=%s GROUP BY code',(actor['tenant_id'],)).fetchall()
            return {'topology':'single PostgreSQL + polling worker','layers':'PostgreSQL prototype; Delta lakehouse planned','outbox':counts,'runs':runs,'quarantine':quarantines}

    @app.get('/api/metrics',response_class=PlainTextResponse)
    def metrics(actor=Depends(authenticate)):
        data=engineering(actor)
        return '# TYPE mhb_outbox_pending gauge\nmhb_outbox_pending '+str(data['outbox']['pending'])+'\n'

    @app.get('/api/architecture')
    def architecture(): return json.loads((ROOT/'architecture/manifest.json').read_text())

    return app
