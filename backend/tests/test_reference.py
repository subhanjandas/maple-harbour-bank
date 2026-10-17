from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import httpx
import pytest
from mhb.reference import fetch,parse

FIXTURE=Path(__file__).resolve().parents[2]/'fixtures/reference/boc-fxusdcad-2026-10-16.json'

def test_recorded_boc_fixture_has_explicit_provenance():
    p=json.loads(FIXTURE.read_text());assert parse(p)==[{'date':'2026-10-16','cad_per_usd':'1.4154'}]
    provenance=json.loads(FIXTURE.with_suffix('.provenance.json').read_text());assert provenance['source']=='Bank of Canada Valet'

def test_cache_bounded_retries_outage_and_no_synthetic_fallback(tmp_path):
    calls=[]
    def respond(req):calls.append(req);return httpx.Response(200,json=json.loads(FIXTURE.read_text()))
    now=datetime(2026,10,17,tzinfo=timezone.utc);path=tmp_path/'fx.json'
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert fetch(path,client,now,sleep=lambda _:None)['status']=='fetched'
        assert fetch(path,client,now+timedelta(hours=1))['status']=='cached'
    assert len(calls)==1
    before=path.read_bytes();failures=[]
    def outage(req):failures.append(req);return httpx.Response(503)
    with httpx.Client(transport=httpx.MockTransport(outage)) as client:
        result=fetch(path,client,now+timedelta(days=2),sleep=lambda _:None)
        assert result['status']=='stale_source_unavailable' and result['outage']
        assert len(failures)==3 and path.read_bytes()==before
        with pytest.raises(RuntimeError,match='NO_CACHE'):fetch(tmp_path/'missing.json',client,now,sleep=lambda _:None)
