"""Bounded Bank of Canada fetch with disk cache and explicit stale provenance.

No rate is executable. No synthetic fallback is permitted.
"""
import argparse
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import random
import tempfile
import time
import httpx

URL='https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=10'

def parse(payload):
    values=[]
    for row in payload['observations']:
        raw=row.get('FXUSDCAD',{}).get('v')
        if raw is None:continue
        value=Decimal(raw)
        if not value.is_finite() or value<=0:raise ValueError('INVALID_REFERENCE_RATE')
        values.append({'date':row['d'],'cad_per_usd':str(value)})
    if not values:raise ValueError('REFERENCE_UNAVAILABLE')
    return values

def fetch(cache:Path,client=None,now=None,sleep=time.sleep):
    now=now or datetime.now(timezone.utc);prior=None
    if cache.exists():
        prior=json.loads(cache.read_text())
        if now-datetime.fromisoformat(prior['captured_at'])<timedelta(hours=24):return {**prior,'status':'cached'}
    owned=client is None;client=client or httpx.Client(timeout=5,follow_redirects=False)
    try:
        for attempt in range(3):
            try:
                response=client.get(URL);response.raise_for_status()
                payload=response.json();values=parse(payload)
                result={'source':'Bank of Canada Valet','series':'FXUSDCAD','url':URL,'captured_at':now.isoformat(),
                        'payload_sha256':hashlib.sha256(response.content).hexdigest(),'observations':values,
                        'convention':'CAD per 1 USD; indicative daily average, not executable','terms':'https://www.bankofcanada.ca/terms/'}
                cache.parent.mkdir(parents=True,exist_ok=True)
                # Atomic replace; a failed fetch never overwrites a prior successful cache.
                with tempfile.NamedTemporaryFile(mode='w',dir=cache.parent,delete=False) as f:
                    temp=Path(f.name);json.dump(result,f,indent=2);f.flush();os.fsync(f.fileno())
                temp.replace(cache)
                return {**result,'status':'fetched'}
            except (httpx.HTTPError,ValueError,KeyError):
                if attempt<2:sleep(random.uniform(.1,.25)*2**attempt)
        if prior:return {**prior,'status':'stale_source_unavailable','outage':True}
        raise RuntimeError('REFERENCE_SOURCE_UNAVAILABLE_NO_CACHE')
    finally:
        if owned:client.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=Path('.runtime/boc-fx.json'));args=p.parse_args()
    print(json.dumps(fetch(args.cache),indent=2))
