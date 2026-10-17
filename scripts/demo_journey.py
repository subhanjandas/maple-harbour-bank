#!/usr/bin/env python3
"""Exercise the actual local core via HTTP. Fixed keys make repeating this demo harmless."""
from contextlib import contextmanager
import argparse
import json
from pathlib import Path
import time
import httpx

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://localhost:8080');p.add_argument('--origin',default='http://localhost:8080');p.add_argument('--output',type=Path,default=Path('evidence/local-journey.json'));args=p.parse_args()

@contextmanager
def login(persona):
    with httpx.Client(base_url=args.base,headers={'Origin':args.origin},timeout=20) as c:
        r=c.post('/api/auth/development/'+persona);r.raise_for_status()
        c.headers['X-CSRF-Token']=c.cookies['mhb_csrf']
        yield c

def post(c,path,key,body=None):
    r=c.post('/api'+path,headers={'Idempotency-Key':key},json=body);r.raise_for_status();return r.json()

with login('alex') as c:
    body={'source_id':'harbour:chequing','beneficiary_id':'harbour:energy','amount_minor':12500,'currency':'CAD','kind':'OUTBOUND'}
    payment=post(c,'/payments','guided-http-payment-01',body)
    assert payment==post(c,'/payments','guided-http-payment-01',body)
    pid=payment['payment_id']
with login('ops') as c:
    settlement=post(c,'/operations/payments/'+pid+'/settle','guided-http-settle-01')
    returned=post(c,'/operations/payments/'+pid+'/returns','guided-http-return-01',{'amount_minor':3000})
with login('engineer') as c:
    until=time.monotonic()+30
    while time.monotonic()<until:
        response=c.get('/api/analytics');response.raise_for_status();analytics=response.json()
        if analytics['publication'] and analytics['publication']['totals']['return_minor']>=3000 and analytics['unpublished_events']==0:break
        time.sleep(.5)
    else:raise RuntimeError('Worker did not publish the expected return within 30 seconds')
with login('alex') as c:
    response=c.get('/api/payments/'+pid);response.raise_for_status();trace=response.json()
    assert all(e['publication_id'] and e['silver_validated'] for e in trace['lineage'])
report={'payment':payment,'settlement':settlement,'return':returned,'publication':analytics['publication']['id'],'trace':trace,
        'boundary':'Actual HTTP core profile; identities and settlement integration are local synthetic simulators'}
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
print('Verified actual HTTP payment → return → worker → publication, including duplicate response and lineage.')
