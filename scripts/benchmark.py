#!/usr/bin/env python3
"""Two separate benchmarks: source-record queries and actual accepted banking commands.

Run in the isolated scale/CI environment. Neither implies maximum sustainable capacity.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import time
from uuid import uuid4
import httpx
import psycopg


def quantiles(samples):
    ordered=sorted(samples)
    return {f'p{p}':ordered[min(len(ordered)-1,math.ceil(len(ordered)*p/100)-1)] for p in [50,95,99]}

def records(url,sizes):
    result=[]
    with psycopg.connect(url,autocommit=True) as db:
        version=db.execute('SELECT version()').fetchone()[0]
        for n in sizes:
            db.execute('CREATE TEMP TABLE mhb_benchmark (event_id bigint,day_no integer,amount_minor bigint)')
            start=time.perf_counter();expected=0;target_count=0
            with db.cursor().copy('COPY mhb_benchmark FROM STDIN') as copy:
                for i in range(n):
                    amount=1+(i*7919)%100000
                    copy.write_row((i,i%365,amount))
                    if i%365==100:expected+=amount;target_count+=1
            load=time.perf_counter()-start
            db.execute('ANALYZE mhb_benchmark')
            before=db.execute("SELECT pg_total_relation_size('mhb_benchmark')").fetchone()[0]
            query='SELECT count(*),coalesce(sum(amount_minor),0) FROM mhb_benchmark WHERE day_no=100'
            all_samples=[];plans=[];index_build=0
            for indexed in [False,True]:
                if indexed:
                    begin=time.perf_counter();db.execute('CREATE INDEX bench_day ON mhb_benchmark(day_no) INCLUDE(amount_minor)');index_build=time.perf_counter()-begin;db.execute('ANALYZE mhb_benchmark')
                for _ in range(2):db.execute(query).fetchone()
                samples=[]
                for _ in range(5):
                    begin=time.perf_counter();answer=db.execute(query).fetchone();samples.append((time.perf_counter()-begin)*1000)
                    assert answer==(target_count,expected),answer
                all_samples.append({'indexed':indexed,'latency_ms':samples,**quantiles(samples)})
                plans.append(db.execute('EXPLAIN (FORMAT JSON) '+query).fetchone()[0])
            after=db.execute("SELECT pg_total_relation_size('mhb_benchmark')").fetchone()[0]
            result.append({'generated_source_records':n,'not_banking_transactions':True,'load_seconds':load,'load_records_per_second':n/load,
                           'distribution':'deterministic uniform modulo 365 days; amount=1+(i*7919)%100000 cents',
                           'query':'one business-day count/sum','warmup_runs':2,'repetitions':5,'samples':all_samples,'query_plans':plans,
                           'expected_count':target_count,'expected_minor':expected,'table_bytes':before,'table_and_index_bytes':after,'index_build_seconds':index_build})
            db.execute('DROP TABLE mhb_benchmark')
    return {'postgresql':version,'measurements':result}


def commands(base,origin,url):
    session=httpx.Client(base_url=base,headers={'Origin':origin},timeout=20)
    response=session.post('/api/auth/development/alex');response.raise_for_status()
    session.headers['X-CSRF-Token']=session.cookies['mhb_csrf']
    body={'source_id':'harbour:chequing','beneficiary_id':'harbour:energy','amount_minor':1,'currency':'CAD','kind':'OUTBOUND'}
    def request(_):
        begin=time.perf_counter();r=session.post('/api/payments',json=body,headers={'Idempotency-Key':str(uuid4())});elapsed=(time.perf_counter()-begin)*1000
        return {'latency_ms':elapsed,'status':r.status_code,'payment_id':r.json().get('payment_id')}
    for i in range(10): assert request(i)['status']==201
    repetitions=[]
    with psycopg.connect(url) as db:
        before=db.execute("SELECT booked_minor FROM accounts WHERE id='harbour:chequing'").fetchone()[0]
        events_before=db.execute('SELECT count(*) FROM outbox').fetchone()[0]
        for repetition in range(3):
            start=time.perf_counter()
            with ThreadPoolExecutor(max_workers=8) as pool: replies=list(pool.map(request,range(100)))
            elapsed=time.perf_counter()-start
            success=[r for r in replies if r['status']==201];lat=[r['latency_ms'] for r in replies]
            assert len(success)==100 and len({r['payment_id'] for r in success})==100
            repetitions.append({'commands':100,'business_transactions':100,'ledger_postings':200,'events':300,'concurrency':8,
                                'duration_seconds':elapsed,'accepted_commands_per_second':100/elapsed,
                                'latency_ms':quantiles(lat),'latency_samples_ms':lat,'errors':len(replies)-len(success)})
        after=db.execute("SELECT booked_minor FROM accounts WHERE id='harbour:chequing'").fetchone()[0]
        events_after=db.execute('SELECT count(*) FROM outbox').fetchone()[0]
        assert before-after==300 and events_after-events_before==900
    session.close()
    return {'workload':'outbound CAD 0.01 instructions on one hot account; worker running concurrently','warmup_commands':10,'repetitions':repetitions,
            'correctness':'300 distinct accepted instructions; 300-cent deposit reduction; 900 new versioned events',
            'limits':'Closed-loop local-network baseline; no claim of saturation, HA, sustained rate, settlement throughput or dashboard concurrency.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sizes',nargs='+',type=int,default=[100000,1000000]);p.add_argument('--api',default='http://127.0.0.1:8000');p.add_argument('--origin',default='http://localhost:5173');p.add_argument('--output',type=Path,default=Path('evidence/benchmark.json'));args=p.parse_args()
    report={'captured_at':datetime.now(timezone.utc).isoformat(),'source_commit':os.getenv('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),
            'host':{'platform':platform.platform(),'cpu_count':os.cpu_count(),'memory_bytes':os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES'),'python':platform.python_version()},
            'source_record_queries':records(os.environ['MIGRATION_DATABASE_URL'],args.sizes),
            'banking_commands':commands(args.api,args.origin,os.environ['MIGRATION_DATABASE_URL'])}
    report['client_peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report['resource_limit']='Client RSS only; container samples are recorded separately. No isolated server peak-memory measurement.'
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2,default=str)+'\n')
    print('Measured separate source-record and banking-command workloads; report:',args.output)
