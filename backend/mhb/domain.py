"""Banking command boundary. PostgreSQL locks protect funds; broker ordering is irrelevant here."""
import hashlib
import json
import time
import random
from datetime import datetime, timezone, date
from uuid import uuid4
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from psycopg.errors import DeadlockDetected, SerializationFailure
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal

TORONTO=ZoneInfo('America/Toronto')

def utcnow(): return datetime.now(timezone.utc)
def business_day(): return utcnow().astimezone(TORONTO).date()
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def identifier(): return str(uuid4())

def deny(code, status=409): raise HTTPException(status, code)

class PaymentCommand(BaseModel):
    model_config=ConfigDict(extra='forbid', strict=True)
    source_id: str = Field(min_length=1,max_length=80)
    kind: Literal['OUTBOUND','INTERNAL']='OUTBOUND'
    beneficiary_id: str | None = Field(default=None,max_length=80)
    destination_id: str | None = Field(default=None,max_length=80)
    amount_minor: int = Field(gt=0,le=100000000)
    currency: Literal['CAD']='CAD'
    @model_validator(mode='after')
    def target(self):
        if self.kind=='OUTBOUND' and (not self.beneficiary_id or self.destination_id is not None): raise ValueError('Outbound requires only beneficiary_id')
        if self.kind=='INTERNAL' and (not self.destination_id or self.beneficiary_id is not None or self.destination_id==self.source_id): raise ValueError('Internal requires a different destination_id')
        return self

class ReturnCommand(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    amount_minor: int = Field(gt=0,le=100000000)

class CorrectionCommand(BaseModel):
    model_config=ConfigDict(extra='forbid')
    reporting_date: date

TRANSITIONS={
 'RECEIVED':{'VALIDATED'},'VALIDATED':{'POSTED'},'POSTED':{'SETTLED','REVERSED'},
 'SETTLED':{'PARTIALLY_RETURNED','RETURNED'},'PARTIALLY_RETURNED':{'PARTIALLY_RETURNED','RETURNED'},
 'RETURNED':set(),'REVERSED':set()
}

def post(db, tenant, payment, kind, amount, debit, credit, correlation, day=None):
    j=identifier()
    db.execute('INSERT INTO journals(id,tenant_id,payment_id,kind,currency,booked_date,correlation_id) VALUES (%s,%s,%s,%s,%s,%s,%s)',
               (j,tenant,payment,kind,'CAD',day or business_day(),correlation))
    db.execute('INSERT INTO journal_lines(journal_id,tenant_id,line_no,ledger_id,direction,amount_minor) VALUES (%s,%s,1,%s,\'DEBIT\',%s),(%s,%s,2,%s,\'CREDIT\',%s)',
               (j,tenant,debit,amount,j,tenant,credit,amount))
    return j

def snapshot(db,p):
    result={k:str(v) if k in {'business_date','created_at','correlation_id'} else v for k,v in p.items()}
    rows=db.execute('SELECT id,amount_minor,booked_date,reporting_date,revision FROM returns WHERE tenant_id=%s AND payment_id=%s ORDER BY id',(p['tenant_id'],p['id'])).fetchall()
    result['returns']=[{**r,'booked_date':str(r['booked_date']),'reporting_date':str(r['reporting_date'])} for r in rows]
    return result

def emit(db,p,actor,status,reason,causation):
    event_id=identifier(); payload=snapshot(db,p); payload['status']=status
    envelope={'schema_version':1,'source_system':'mhb-core','event_id':event_id,
              'aggregate_id':p['id'],'aggregate_version':p['version'],'tenant_id':p['tenant_id'],
              'event_type':'payment.snapshot','reason':reason,'event_time':utcnow().isoformat(),
              'correlation_id':str(p['correlation_id']),'causation_id':causation,
              'currency':'CAD','currency_exponent':2,'payload':payload}
    db.execute('INSERT INTO payment_events(id,tenant_id,payment_id,version,status,actor_id,reason,occurred_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
               (event_id,p['tenant_id'],p['id'],p['version'],status,actor['id'],reason,utcnow()))
    db.execute('INSERT INTO outbox(event_id,tenant_id,aggregate_id,aggregate_version,envelope,checksum,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)',
               (event_id,p['tenant_id'],p['id'],p['version'],Jsonb(envelope),digest(envelope),utcnow()))
    return event_id

def audit(db,actor,action,resource,correlation):
    db.execute('INSERT INTO audit(tenant_id,actor_id,action,resource_id,correlation_id) VALUES (%s,%s,%s,%s,%s)',
               (actor['tenant_id'],actor['id'],action,resource,correlation))

def visible_payment(db,actor,payment_id,lock=False):
    p=db.execute('SELECT * FROM payments WHERE id=%s AND tenant_id=%s'+(' FOR UPDATE' if lock else ''),(payment_id,actor['tenant_id'])).fetchone()
    if not p or (actor['role']=='customer' and p['owner_id']!=actor['id']) or (actor['role']=='operations' and p['scope']!=actor['scope']): deny('PAYMENT_NOT_FOUND',404)
    return p

def idempotent(database,actor,key,body,action,work):
    if not 8<=len(key)<=100: deny('IDEMPOTENCY_KEY_REQUIRED_8_TO_100_CHARS',422)
    fingerprint=digest({'action':action,'body':body})
    for attempt in range(3):
        try:
            with database.transaction(actor['tenant_id']) as db:
                # Transaction-scoped key lock precedes resource locks for duplicate storms.
                db.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(actor['tenant_id']+':'+actor['id']+':'+key,))
                prior=db.execute('SELECT * FROM commands WHERE tenant_id=%s AND actor_id=%s AND key=%s',(actor['tenant_id'],actor['id'],key)).fetchone()
                if prior:
                    if prior['request_hash']!=fingerprint: deny('IDEMPOTENCY_CONFLICT')
                    return prior['response']
                response=work(db)
                db.execute('INSERT INTO commands VALUES (%s,%s,%s,%s,%s,now())',(actor['tenant_id'],actor['id'],key,fingerprint,Jsonb(response)))
                return response
        except (DeadlockDetected,SerializationFailure):
            if attempt==2: deny('RETRYABLE_CONTENTION',503)
            time.sleep(random.uniform(.01,.04)*(2**attempt))

def create_payment(database,actor,key,command):
    if actor['role']!='customer': deny('CUSTOMER_REQUIRED',403)
    def work(db):
        tenant=actor['tenant_id']; target=command.destination_id
        ids=sorted({command.source_id,*([target] if target else [])})
        rows=db.execute('SELECT * FROM accounts WHERE tenant_id=%s AND id=ANY(%s) ORDER BY id FOR UPDATE',(tenant,ids)).fetchall()
        accounts={a['id']:a for a in rows}
        if len(accounts)!=len(ids) or any(a['owner_id']!=actor['id'] for a in rows): deny('ACCOUNT_NOT_FOUND',404)
        if any(a['status']!='OPEN' or a['currency']!=command.currency for a in rows): deny('ACCOUNT_UNAVAILABLE')
        source=accounts[command.source_id]
        if source['booked_minor']-source['hold_minor']<command.amount_minor: deny('INSUFFICIENT_AVAILABLE_FUNDS')
        if command.kind=='OUTBOUND' and not db.execute('SELECT 1 FROM beneficiaries WHERE tenant_id=%s AND owner_id=%s AND id=%s',(tenant,actor['id'],command.beneficiary_id)).fetchone(): deny('BENEFICIARY_NOT_FOUND',404)
        pid=identifier(); correlation=identifier()
        p=db.execute('''INSERT INTO payments(id,tenant_id,owner_id,source_id,destination_id,beneficiary_id,kind,amount_minor,currency,business_date,status,version,correlation_id,scope,created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'POSTED',3,%s,%s,%s) RETURNING *''',
        (pid,tenant,actor['id'],source['id'],target,command.beneficiary_id,command.kind,command.amount_minor,command.currency,business_day(),correlation,source['scope'],utcnow())).fetchone()
        credit=accounts[target]['ledger_id'] if target else tenant+':clearing'
        post(db,tenant,pid,'PAYMENT',command.amount_minor,source['ledger_id'],credit,correlation)
        db.execute('UPDATE accounts SET booked_minor=booked_minor-%s WHERE id=%s',(command.amount_minor,source['id']))
        if target: db.execute('UPDATE accounts SET booked_minor=booked_minor+%s WHERE id=%s',(command.amount_minor,target))
        cause=correlation
        for v,status in enumerate(['RECEIVED','VALIDATED','POSTED'],1):
            cause=emit(db,{**p,'version':v},actor,status,'CUSTOMER_COMMAND',cause)
        audit(db,actor,'PAYMENT_POSTED',pid,correlation)
        return {'payment_id':pid,'status':'POSTED','amount_minor':command.amount_minor,'currency':'CAD','correlation_id':correlation}
    return idempotent(database,actor,key,command.model_dump(),'payment',work)

def operate(database,actor,pid,key,action,body=None):
    if actor['role']!='operations': deny('OPERATIONS_REQUIRED',403)
    def work(db):
        p=visible_payment(db,actor,pid,True); tenant=actor['tenant_id']; corr=identifier()
        locked=db.execute('SELECT * FROM accounts WHERE tenant_id=%s AND id=ANY(%s) ORDER BY id FOR UPDATE',(tenant,sorted({p['source_id'],*([p['destination_id']] if p['destination_id'] else [])}))).fetchall()
        source=next(a for a in locked if a['id']==p['source_id'])
        if action=='settle':
            if p['kind']!='OUTBOUND' or 'SETTLED' not in TRANSITIONS[p['status']]: deny('INVALID_TRANSITION')
            post(db,tenant,pid,'SETTLEMENT',p['amount_minor'],tenant+':clearing',tenant+':cash',corr)
            new='SETTLED'
        elif action=='return':
            if p['kind']!='OUTBOUND' or p['status'] not in {'SETTLED','PARTIALLY_RETURNED'}: deny('INVALID_TRANSITION')
            if db.execute('SELECT count(*) n FROM returns WHERE tenant_id=%s AND payment_id=%s',(tenant,pid)).fetchone()['n']>=100: deny('RETURN_INSTALLMENT_LIMIT')
            amount=body['amount_minor']; total=p['returned_minor']+amount
            if total>p['amount_minor']: deny('RETURN_EXCEEDS_PAYMENT')
            rid=identifier()
            db.execute('INSERT INTO returns VALUES (%s,%s,%s,%s,%s,%s,1)',(rid,tenant,pid,amount,business_day(),business_day()))
            post(db,tenant,pid,'RETURN',amount,tenant+':cash',source['ledger_id'],corr)
            db.execute('UPDATE accounts SET booked_minor=booked_minor+%s WHERE id=%s',(amount,source['id']))
            p['returned_minor']=total; new='RETURNED' if total==p['amount_minor'] else 'PARTIALLY_RETURNED'
        elif action=='reverse':
            if p['kind']!='INTERNAL' or p['status']!='POSTED': deny('INVALID_TRANSITION')
            # Re-lock both accounts in canonical order. Payment lock serializes operations.
            rows=db.execute('SELECT * FROM accounts WHERE tenant_id=%s AND id=ANY(%s) ORDER BY id FOR UPDATE',(tenant,sorted([p['source_id'],p['destination_id']]))).fetchall()
            dest=next(a for a in rows if a['id']==p['destination_id'])
            if dest['booked_minor']-dest['hold_minor']<p['amount_minor']: deny('DESTINATION_FUNDS_UNAVAILABLE')
            post(db,tenant,pid,'REVERSAL',p['amount_minor'],dest['ledger_id'],source['ledger_id'],corr)
            db.execute('UPDATE accounts SET booked_minor=booked_minor-%s WHERE id=%s',(p['amount_minor'],dest['id']))
            db.execute('UPDATE accounts SET booked_minor=booked_minor+%s WHERE id=%s',(p['amount_minor'],source['id']))
            new='REVERSED'
        else: deny('UNKNOWN_OPERATION',422)
        p=db.execute('UPDATE payments SET status=%s,version=version+1,returned_minor=%s WHERE id=%s RETURNING *',(new,p['returned_minor'],pid)).fetchone()
        event=emit(db,p,actor,new,'SIMULATOR_'+action.upper(),corr)
        audit(db,actor,action.upper(),pid,corr)
        return {'payment_id':pid,'status':new,'returned_minor':p['returned_minor'],'event_id':event,'correlation_id':corr}
    return idempotent(database,actor,key,body or {},action+':'+pid,work)

def correct_return(database,actor,pid,rid,key,day):
    if actor['role']!='operations': deny('OPERATIONS_REQUIRED',403)
    def work(db):
        p=visible_payment(db,actor,pid,True)
        if not p['business_date']<=day<=business_day(): deny('REPORTING_DATE_OUTSIDE_PAYMENT_LIFETIME',422)
        r=db.execute('UPDATE returns SET reporting_date=%s,revision=revision+1 WHERE tenant_id=%s AND id=%s AND payment_id=%s RETURNING *',(day,actor['tenant_id'],rid,pid)).fetchone()
        if not r: deny('RETURN_NOT_FOUND',404)
        p=db.execute('UPDATE payments SET version=version+1 WHERE id=%s RETURNING *',(pid,)).fetchone()
        corr=identifier();event=emit(db,p,actor,p['status'],'REPORTING_DATE_CORRECTION',corr)
        audit(db,actor,'RETURN_REPORTING_CORRECTED',rid,corr)
        return {'payment_id':pid,'return_id':rid,'reporting_date':str(day),'event_id':event,'correlation_id':corr}
    return idempotent(database,actor,key,{'return_id':rid,'reporting_date':str(day)},'reporting-correction:'+pid,work)
