"""Operator-only OIDC visitor provisioning; no public enrollment or staff role creation.

Run with schema-owner credentials and a protected request JSON file. Identity claims
never choose a tenant or role. Repeating an issuer/subject never re-funds or reactivates.
"""
import argparse
import json
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .domain import identifier, post, utcnow


class VisitorRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    issuer: str = Field(min_length=1, max_length=500)
    subject: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=80)
    operator_label: str = Field(min_length=1, max_length=80)
    lifetime_days: int = Field(default=7, ge=1, le=30)
    event_limit: int = Field(default=3000, ge=3, le=50000)

    @field_validator('issuer', 'subject', 'display_name', 'operator_label')
    @classmethod
    def clean_text(cls, value):
        if value != value.strip() or any(ord(c)<32 or ord(c)==127 for c in value):
            raise ValueError('No surrounding whitespace or control characters')
        return value


def provision(request: VisitorRequest, url=None, *, allow_loopback_test_issuer=False):
    parsed = urlsplit(request.issuer)
    loopback = allow_loopback_test_issuer and parsed.scheme == 'http' and parsed.hostname in {'localhost', '127.0.0.1'}
    if (parsed.scheme != 'https' and not loopback) or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('HTTPS_ISSUER_REQUIRED')
    with psycopg.connect(url or os.environ['MIGRATION_DATABASE_URL'], row_factory=dict_row) as db:
        # Serialize admission including retries; count all retained scenarios, not only
        # active visitors. Expiry must not turn into unlimited storage/funding churn.
        capacity = db.execute('SELECT scenario_limit FROM visitor_capacity WHERE singleton FOR UPDATE').fetchone()
        existing = db.execute('SELECT p.id,p.tenant_id,v.expires_at FROM principals p LEFT JOIN visitor_scenarios v ON v.principal_id=p.id WHERE p.issuer=%s AND p.subject=%s', (request.issuer, request.subject)).fetchone()
        if existing:
            if existing['expires_at'] is None:
                raise ValueError('IDENTITY_ALREADY_ASSIGNED')
            return {'principal_id': existing['id'], 'tenant_id': existing['tenant_id'], 'created': False}
        count = db.execute('SELECT count(*) n FROM visitor_scenarios').fetchone()['n']
        if count >= capacity['scenario_limit']:
            raise ValueError('VISITOR_CAPACITY_REACHED')
        tenant = 'visitor-' + identifier()
        principal = tenant + ':customer'
        db.execute('INSERT INTO tenants(id,name) VALUES (%s,%s)', (tenant, 'Isolated synthetic visitor scenario'))
        db.execute("INSERT INTO principals(id,tenant_id,name,role,issuer,subject) VALUES (%s,%s,%s,'customer',%s,%s)", (principal, tenant, request.display_name, request.issuer, request.subject))
        db.execute('INSERT INTO visitor_scenarios(tenant_id,principal_id,expires_at) VALUES (%s,%s,%s)', (tenant, principal, utcnow()+timedelta(days=request.lifetime_days)))
        db.execute('INSERT INTO scenario_limits(tenant_id,event_limit) VALUES (%s,%s)', (tenant, request.event_limit))
        for kind, label in [('cash', 'Simulated settlement cash'), ('clearing', 'Outbound clearing')]:
            db.execute('INSERT INTO ledger_accounts VALUES (%s,%s,%s,%s)', (tenant+':'+kind, tenant, 'ASSET' if kind=='cash' else 'LIABILITY', label))
        for kind, label, amount in [('chequing', 'Everyday Chequing', 500000), ('savings', 'Harbour Savings', 1250000)]:
            aid = tenant+':'+kind
            db.execute("INSERT INTO ledger_accounts VALUES (%s,%s,'LIABILITY',%s)", (aid, tenant, label))
            db.execute('INSERT INTO accounts(id,tenant_id,owner_id,ledger_id,label,booked_minor) VALUES (%s,%s,%s,%s,%s,%s)', (aid, tenant, principal, aid, label, amount))
            post(db, tenant, None, 'OPENING', amount, tenant+':cash', aid, identifier())
        db.execute('INSERT INTO beneficiaries VALUES (%s,%s,%s,%s)', (tenant+':energy', tenant, principal, 'Harbour Energy · simulator'))
        db.execute("INSERT INTO scenario_admin_events(id,tenant_id,action,operator_label) VALUES (%s,%s,'PROVISION',%s)", (identifier(), tenant, request.operator_label))
        return {'principal_id': principal, 'tenant_id': tenant, 'created': True}


def deactivate(tenant, operator_label, url=None):
    # Reuse strict text validation. The label is an operator attestation, not an
    # authenticated identity; schema-owner access is the actual trust boundary.
    VisitorRequest(issuer='https://unused.example', subject='unused', display_name='unused', operator_label=operator_label)
    with psycopg.connect(url or os.environ['MIGRATION_DATABASE_URL'], row_factory=dict_row) as db:
        row = db.execute('SELECT * FROM visitor_scenarios WHERE tenant_id=%s FOR UPDATE', (tenant,)).fetchone()
        if not row:
            raise ValueError('VISITOR_NOT_FOUND')
        if row['disabled_at'] is not None:
            return {'tenant_id': tenant, 'changed': False}
        db.execute('UPDATE visitor_scenarios SET disabled_at=now() WHERE tenant_id=%s', (tenant,))
        db.execute('UPDATE principals SET active=false WHERE id=%s', (row['principal_id'],))
        db.execute('UPDATE sessions SET revoked_at=now() WHERE principal_id=%s AND revoked_at IS NULL', (row['principal_id'],))
        db.execute("INSERT INTO scenario_admin_events(id,tenant_id,action,operator_label) VALUES (%s,%s,'DEACTIVATE',%s)", (identifier(), tenant, operator_label))
        return {'tenant_id': tenant, 'changed': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    create = sub.add_parser('create')
    create.add_argument('--request-file', type=Path, required=True)
    disable = sub.add_parser('deactivate')
    disable.add_argument('--tenant', required=True)
    disable.add_argument('--operator-label', required=True)
    args = parser.parse_args()
    try:
        if args.action == 'create':
            if args.request_file.stat().st_size > 8192:
                raise ValueError('REQUEST_FILE_TOO_LARGE')
            result = provision(VisitorRequest.model_validate_json(args.request_file.read_bytes()))
        else:
            result = deactivate(args.tenant, args.operator_label)
    except (ValueError, OSError, psycopg.Error):
        # Avoid logging subject identifiers, request contents, connection strings,
        # constraint details or secrets through a failed operator command.
        parser.exit(1, 'Provisioning failed; check the protected request, capacity and database access. No partial changes committed.\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
