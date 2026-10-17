"""A real authorization-code exchange against an isolated signed-token test provider.

This verifies the relying-party library flow, not a deployed identity provider.
"""
import base64
import hashlib
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlencode,urlparse,parse_qs
import pytest
from authlib.jose import JsonWebKey,jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from mhb.api import create_app
from mhb.config import Settings

@pytest.fixture
def provider():
    private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    pem=private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    pub=private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    jwk=JsonWebKey.import_key(pub,{'kid':'test-key'}).as_dict()
    state={'nonce':'','challenge':'','variant':'valid','pkce_verified':False}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send_json(self,value):
            data=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if self.path=='/.well-known/openid-configuration':self.send_json({'issuer':state['issuer'],'authorization_endpoint':state['issuer']+'/authorize','token_endpoint':state['issuer']+'/token','jwks_uri':state['issuer']+'/jwks','response_types_supported':['code'],'subject_types_supported':['public'],'id_token_signing_alg_values_supported':['RS256'],'code_challenge_methods_supported':['S256']})
            elif self.path=='/jwks':self.send_json({'keys':[jwk]})
            else:self.send_error(404)
        def do_POST(self):
            q=parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode());v=q.get('code_verifier',[''])[0]
            actual=base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b'=').decode()
            state['pkce_verified']=actual==state['challenge'] and bool(v)
            now=int(time.time());claims={'iss':state['issuer'],'sub':'synthetic-oidc-alex','aud':'maple-harbour','exp':now+300,'iat':now,'nonce':state['nonce']}
            variant=state['variant']
            if variant=='expired':claims['exp']=now-3600
            if variant=='audience':claims['aud']='another-client'
            if variant=='nonce':claims['nonce']='wrong'
            if variant=='issuer':claims['iss']='https://attacker.example'
            token=jwt.encode({'alg':'RS256','kid':'test-key'},claims,pem).decode()
            if variant=='signature':token=token[:-10]+'AAAAAAAAAA'
            self.send_json({'access_token':'synthetic-access-token','token_type':'Bearer','expires_in':300,'id_token':token})
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);state['issuer']='http://127.0.0.1:'+str(server.server_port)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield state
    finally:server.shutdown();server.server_close();thread.join()

@pytest.mark.parametrize('variant,expected',[('valid',303),('expired',401),('audience',401),('nonce',401),('issuer',401),('signature',401),('state',401),('unmapped',403)])
def test_oidc_code_pkce_and_token_validation(urls,dbs,admin,provider,variant,expected):
    provider['variant']=variant
    if variant!='unmapped':admin.execute("UPDATE principals SET issuer=%s,subject='synthetic-oidc-alex' WHERE id='harbour:alex'",(provider['issuer'],))
    settings=Settings(database_url=urls['api'],session_secret=secrets.token_hex(40),origin='http://localhost:8080',demo_auth=False,oidc_issuer=provider['issuer'])
    with TestClient(create_app(settings),base_url=settings.origin,follow_redirects=False) as client:
        start=client.get('/api/auth/login');assert start.status_code in {302,307}
        query=parse_qs(urlparse(start.headers['location']).query)
        assert query['code_challenge_method']==['S256']
        provider['challenge']=query['code_challenge'][0];provider['nonce']=query['nonce'][0]
        response=client.get('/api/auth/callback?'+urlencode({'code':'test-code','state':'wrong-state' if variant=='state' else query['state'][0]}))
        assert response.status_code==expected,response.text
        if variant!='state':assert provider['pkce_verified']
        if variant=='valid':
            assert client.get('/api/me').json()['id']=='harbour:alex'
            # OIDC alone does not enable the local persona switcher.
            assert client.post('/api/auth/development/ops').status_code==404
