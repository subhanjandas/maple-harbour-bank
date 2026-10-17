"""Idempotent synthetic funding. Seed is an explicit operator action, never an API startup hook."""
import os
import argparse
import psycopg
from psycopg.rows import dict_row
from .domain import post, identifier

PEOPLE=[('alex','Subhanjan Das','customer','TORONTO'),('sam','Sam Chen','customer','TORONTO'),
        ('ops','Taylor Reid','operations','TORONTO'),('analyst','Jordan Martin','analyst','TORONTO'),
        ('engineer','Casey Roy','engineer','TORONTO'),('ops-west','Morgan Lee','operations','VANCOUVER')]

def seed(url=None):
    with psycopg.connect(url or os.environ['MIGRATION_DATABASE_URL'],row_factory=dict_row) as db:
        db.execute('SELECT pg_advisory_xact_lock(420011)')
        for tenant in ['harbour','other']:
            db.execute('INSERT INTO tenants VALUES (%s,%s) ON CONFLICT DO NOTHING',(tenant,tenant.title()+' synthetic scenario'))
            for name,label,role,scope in PEOPLE:
                db.execute('INSERT INTO principals(id,tenant_id,name,role,scope) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(tenant+':'+name,tenant,label,role,scope))
            for kind,label in [('cash','Simulated settlement cash'),('clearing','Outbound clearing')]:
                db.execute('INSERT INTO ledger_accounts VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',(tenant+':'+kind,tenant,'ASSET' if kind=='cash' else 'LIABILITY',label))
            for name,owner,label,amount in [('chequing','alex','Everyday Chequing',500000),('savings','alex','Harbour Savings',1250000),('sam','sam','Everyday Chequing',300000)]:
                aid=tenant+':'+name
                db.execute('INSERT INTO ledger_accounts VALUES (%s,%s,\'LIABILITY\',%s) ON CONFLICT DO NOTHING',(aid,tenant,label))
                exists=db.execute('SELECT 1 FROM accounts WHERE id=%s',(aid,)).fetchone()
                if not exists:
                    db.execute('INSERT INTO accounts(id,tenant_id,owner_id,ledger_id,label,booked_minor) VALUES (%s,%s,%s,%s,%s,%s)',(aid,tenant,tenant+':'+owner,aid,label,amount))
                    post(db,tenant,None,'OPENING',amount,tenant+':cash',aid,identifier())
            db.execute('INSERT INTO beneficiaries VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',(tenant+':energy',tenant,tenant+':alex','Harbour Energy · simulator'))
    print('Seeded two isolated synthetic scenarios; no real identities or funds.')

if __name__=='__main__': seed()
