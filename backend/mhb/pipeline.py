"""At-least-once archive, versioned projections and atomic publication.

This release uses PostgreSQL Bronze/Silver/Gold prototype tables, NOT Spark/Delta.
The source control is captured independently from the consumer's inputs.
"""
import argparse
import json
import logging
import os
import random
import signal
import time
from collections import defaultdict
from datetime import date, timedelta
from psycopg.types.json import Jsonb
from .db import Database
from .domain import digest, identifier, TRANSITIONS
from .contracts import Envelope

LOG=logging.getLogger('mhb.worker')

class Rejected(Exception):
    def __init__(self,code,event_id=None): self.code=code; self.event_id=event_id; super().__init__(code)

def archive_one(database,failpoint=None):
    """Archive commits before source acknowledgement. A crash here causes safe redelivery."""
    with database.transaction() as db:
        row=db.execute('SELECT * FROM outbox WHERE acknowledged_at IS NULL AND retry_at<=now() ORDER BY seq FOR UPDATE SKIP LOCKED LIMIT 1').fetchone()
        if row is None: return False
        old=db.execute('SELECT checksum FROM bronze WHERE event_id=%s',(row['event_id'],)).fetchone()
        if old and old['checksum']!=row['checksum']: raise Rejected('EVENT_ID_CONFLICT',row['event_id'])
        db.execute('INSERT INTO bronze(event_id,tenant_id,source_seq,checksum,envelope,ingestion_run_id) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(event_id) DO NOTHING',
                   (row['event_id'],row['tenant_id'],row['seq'],row['checksum'],Jsonb(row['envelope']),identifier()))
        db.execute('UPDATE outbox SET attempts=attempts+1 WHERE seq=%s',(row['seq'],))
    if failpoint: failpoint()  # Deliberately after committed sink, before source ack.
    with database.transaction() as db:
        db.execute('UPDATE outbox SET acknowledged_at=now(),last_error=NULL WHERE seq=%s',(row['seq'],))
    return True

def make_daily(current):
    days=defaultdict(lambda:{'instruction_count':0,'instruction_minor':0,'return_count':0,'return_minor':0,'settled_count':0})
    for p in current:
        if p['status'] not in {'RECEIVED','VALIDATED'}:
            d=days[p['business_date']]; d['instruction_count']+=1; d['instruction_minor']+=p['amount_minor']
            d['settled_count']+=int(p['status'] in {'SETTLED','PARTIALLY_RETURNED','RETURNED'})
        for r in p['returns']:
            d=days[r['reporting_date']]; d['return_count']+=1;d['return_minor']+=r['amount_minor']
    return [{'business_date':str(day),'channel':'WEB','currency':'CAD',**v} for day,v in sorted(days.items())]

def source_controls(rows): return digest([(r['seq'],str(r['event_id']),r['checksum']) for r in rows])

def publish(database,tenant,failpoint=None,force=False):
    run=identifier();source=[];cutoff=0;checksum=digest([])
    try:
        with database.transaction() as db:
            # All publication reads are one consistent snapshot. Concurrent commands become the next cutoff.
            db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            db.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,42))',(tenant,))
            source=db.execute('SELECT seq,event_id,checksum,created_at FROM outbox WHERE tenant_id=%s ORDER BY seq',(tenant,)).fetchall()
            cutoff=source[-1]['seq'] if source else 0;checksum=source_controls(source)
            previous=db.execute('SELECT p.* FROM serving_pointer s JOIN publications p ON p.id=s.publication_id WHERE s.tenant_id=%s',(tenant,)).fetchone()
            if previous and previous['source_checksum']==checksum and not force: return {'status':'UNCHANGED','publication_id':str(previous['id'])}
            bronze=db.execute('SELECT * FROM bronze WHERE tenant_id=%s AND source_seq<=%s ORDER BY source_seq',(tenant,cutoff)).fetchall()
            actual=digest([(r['source_seq'],str(r['event_id']),r['checksum']) for r in bronze])
            if len(source)!=len(bronze) or actual!=checksum: raise Rejected('MISSING_OR_CHANGED_SOURCE')
            by_payment=defaultdict(list)
            for row in bronze:
                raw=row['envelope']
                if digest(raw)!=row['checksum']: raise Rejected('PAYLOAD_CHECKSUM_MISMATCH',row['event_id'])
                try: envelope=Envelope.model_validate(raw)
                except Exception: raise Rejected('CONTRACT_V1_REJECTED',row['event_id']) from None
                if str(envelope.event_id)!=str(row['event_id']) or envelope.tenant_id!=tenant: raise Rejected('ENVELOPE_IDENTITY_CONFLICT',row['event_id'])
                by_payment[envelope.aggregate_id].append(row)
            current=[]
            for pid,versions in by_payment.items():
                versions.sort(key=lambda r:r['envelope']['aggregate_version']); prior=None
                for expected,row in enumerate(versions,1):
                    e=row['envelope'];p=e['payload']
                    if e['aggregate_version']!=expected: raise Rejected('AGGREGATE_VERSION_GAP',row['event_id'])
                    if prior is None and p['status']!='RECEIVED': raise Rejected('LIFECYCLE_INITIAL_STATE',row['event_id'])
                    if prior:
                        immutable=['id','tenant_id','owner_id','source_id','destination_id','beneficiary_id','kind','amount_minor','currency','business_date','created_at']
                        if any(prior[k]!=p[k] for k in immutable): raise Rejected('IMMUTABLE_PAYMENT_CHANGED',row['event_id'])
                        correction=e['reason']=='REPORTING_DATE_CORRECTION'
                        if p['status'] not in TRANSITIONS[prior['status']] and not (correction and p['status']==prior['status']): raise Rejected('LIFECYCLE_TRANSITION',row['event_id'])
                        if correction and (p['returned_minor']!=prior['returned_minor'] or [(r['id'],r['amount_minor'],r['booked_date']) for r in p['returns']]!=[(r['id'],r['amount_minor'],r['booked_date']) for r in prior['returns']]): raise Rejected('CORRECTION_CHANGED_CASH',row['event_id'])
                    prior=p
                    existing=db.execute('SELECT checksum FROM silver_history WHERE tenant_id=%s AND aggregate_id=%s AND aggregate_version=%s',(tenant,pid,expected)).fetchone()
                    if existing and existing['checksum']!=row['checksum']: raise Rejected('REVISION_CONFLICT',row['event_id'])
                    db.execute('INSERT INTO silver_history VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(event_id) DO NOTHING',
                               (row['event_id'],tenant,pid,expected,row['checksum'],Jsonb(e)))
                latest=versions[-1];p=latest['envelope']['payload']; current.append(p)
                db.execute('''INSERT INTO silver_current VALUES (%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,aggregate_id)
                 DO UPDATE SET version=EXCLUDED.version,payload=EXCLUDED.payload,event_id=EXCLUDED.event_id
                 WHERE silver_current.version<=EXCLUDED.version''',(tenant,pid,p['version'],Jsonb(p),latest['event_id']))
            daily=make_daily(current)
            totals={k:sum(d[k] for d in daily) for k in ['instruction_count','instruction_minor','return_count','return_minor','settled_count']}
            # Independent source-envelope aggregation; never sum every payment snapshot as new money.
            source_latest={}
            for row in db.execute('SELECT envelope FROM outbox WHERE tenant_id=%s AND seq<=%s ORDER BY seq',(tenant,cutoff)):
                p=row['envelope']['payload'];old=source_latest.get(p['id'])
                if not old or p['version']>old['version']:source_latest[p['id']]=p
            expected_pay=sum(p['amount_minor'] for p in source_latest.values() if p['status'] not in {'RECEIVED','VALIDATED'})
            expected_ret=sum(p['returned_minor'] for p in source_latest.values())
            if totals['instruction_minor']!=expected_pay or totals['return_minor']!=expected_ret: raise Rejected('FINANCIAL_CONTROL_MISMATCH')
            totals['reconciled']=True;totals['metric_semantics']='Accepted instruction activity; not settled cash flow'
            db.execute('INSERT INTO pipeline_runs(id,tenant_id,status,cutoff,source_count,source_checksum) VALUES (%s,%s,\'SUCCEEDED\',%s,%s,%s)',(run,tenant,cutoff,len(source),checksum))
            pub=identifier()
            db.execute('INSERT INTO publications(id,tenant_id,run_id,cutoff,source_count,source_checksum,source_cutoff_at,daily,totals) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                       (pub,tenant,run,cutoff,len(source),checksum,source[-1]['created_at'] if source else None,Jsonb(daily),Jsonb(totals)))
            if failpoint: failpoint()
            db.execute('INSERT INTO serving_pointer VALUES (%s,%s) ON CONFLICT(tenant_id) DO UPDATE SET publication_id=EXCLUDED.publication_id',(tenant,pub))
        LOG.info(json.dumps({'event':'publication.succeeded','tenant':tenant,'run_id':run,'publication_id':pub,'source_count':len(source)}))
        return {'status':'SUCCEEDED','publication_id':pub,'run_id':run}
    except Rejected as e:
        with database.transaction() as db:
            db.execute('INSERT INTO pipeline_runs VALUES (%s,%s,\'REJECTED\',%s,%s,%s,%s,now())',(run,tenant,cutoff,len(source),checksum,Jsonb([e.code])))
            db.execute('INSERT INTO quarantine(tenant_id,run_id,event_id,code) VALUES (%s,%s,%s,%s)',(tenant,run,e.event_id,e.code))
        LOG.warning(json.dumps({'event':'publication.rejected','run_id':run,'code':e.code}))
        return {'status':'REJECTED','run_id':run,'code':e.code}

def cycle(database,limit=100):
    archived=0
    for _ in range(limit):
        if not archive_one(database): break
        archived+=1
    with database.transaction() as db: tenants=[r['id'] for r in db.execute('SELECT id FROM tenants')]
    return {'archived':archived,'publications':[publish(database,t) for t in tenants]}

def backfill(database,tenant,start,end):
    days=(end-start).days+1
    if not 1<=days<=31: raise ValueError('BACKFILL_LIMIT_31_DAYS')
    # Full current-state rebuild is intentional at this scale; range is recorded by the CLI caller.
    return publish(database,tenant,force=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--once',action='store_true')
    parser.add_argument('--backfill',nargs=3,metavar=('TENANT','START','END'))
    args=parser.parse_args(); logging.basicConfig(level=logging.INFO,format='%(message)s')
    database=Database(os.environ['WORKER_DATABASE_URL']);database.pool.open(wait=True)
    stop=False
    def halt(*_):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGTERM,halt);signal.signal(signal.SIGINT,halt)
    try:
        if args.backfill:
            tenant,start,end=args.backfill;print(backfill(database,tenant,date.fromisoformat(start),date.fromisoformat(end)));return
        failures=0
        while not stop:
            try:
                result=cycle(database); failures=0
                if args.once: print(json.dumps(result));break
                time.sleep(1 if result['archived'] else 3)
            except Exception as e:
                failures+=1;LOG.error(json.dumps({'event':'worker.retry','exception_type':type(e).__name__,'attempt':failures}))
                if args.once: raise
                time.sleep(random.uniform(.5,1)*min(30,2**min(failures,5)))
    finally: database.pool.close()

if __name__=='__main__': main()
