"""Opaque, revocable server sessions. Roles and scope come only from the database."""
import hashlib
import secrets
from datetime import timedelta
from fastapi import HTTPException, Request
from .domain import utcnow

COOKIE='mhb_session'
def hash_token(value): return hashlib.sha256(value.encode()).hexdigest()

def create_session(database,principal,response,secure):
    token=secrets.token_urlsafe(40); csrf=secrets.token_urlsafe(32)
    with database.transaction() as db:
        db.execute('INSERT INTO sessions(token_hash,principal_id,csrf_hash,expires_at) VALUES (%s,%s,%s,%s)',
                   (hash_token(token),principal['id'],hash_token(csrf),utcnow()+timedelta(minutes=30)))
    response.set_cookie(COOKIE,token,max_age=1800,httponly=True,secure=secure,samesite='lax',path='/')
    response.set_cookie('mhb_csrf',csrf,max_age=1800,httponly=False,secure=secure,samesite='lax',path='/')

def authenticate(request: Request):
    token=request.cookies.get(COOKIE,'')
    if not token: raise HTTPException(401,'AUTHENTICATION_REQUIRED')
    database=request.app.state.db
    with database.transaction() as db:
        row=db.execute('''SELECT p.*,s.csrf_hash FROM sessions s JOIN principals p ON p.id=s.principal_id
        WHERE s.token_hash=%s AND s.revoked_at IS NULL AND s.expires_at>now() AND p.active''',(hash_token(token),)).fetchone()
        if not row: raise HTTPException(401,'SESSION_EXPIRED_OR_REVOKED')
        # Shared durable limit, works across API processes. Not a public-edge DDoS defence.
        rate=db.execute('''INSERT INTO rate_windows VALUES (%s,date_trunc('minute',now()),1)
          ON CONFLICT(bucket) DO UPDATE SET window_at=date_trunc('minute',now()),
          hits=CASE WHEN rate_windows.window_at=date_trunc('minute',now()) THEN rate_windows.hits+1 ELSE 1 END RETURNING hits''',('principal:'+row['id'],)).fetchone()
    if rate['hits']>request.app.state.settings.request_limit: raise HTTPException(429,'RATE_LIMITED',headers={'Retry-After':'60'})
    if request.method not in {'GET','HEAD','OPTIONS'}:
        origin=request.headers.get('origin')
        if origin!=request.app.state.settings.origin: raise HTTPException(403,'ORIGIN_DENIED')
        csrf=request.headers.get('x-csrf-token','')
        if not secrets.compare_digest(hash_token(csrf),row['csrf_hash']): raise HTTPException(403,'CSRF_DENIED')
    return row

def require(actor,*roles):
    if actor['role'] not in roles: raise HTTPException(403,'ROLE_DENIED')
