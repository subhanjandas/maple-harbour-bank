#!/usr/bin/env python3
"""Generate ignored local secrets without printing them. Standard-library only."""
from pathlib import Path
import secrets
root=Path(__file__).resolve().parents[1]
p=root/'.env'
if p.exists(): raise SystemExit('.env already exists; kept existing secrets')
password=secrets.token_hex(24)
api=secrets.token_hex(24);worker=secrets.token_hex(24)
p.write_text(f'''POSTGRES_PASSWORD={password}
API_PASSWORD={api}
WORKER_PASSWORD={worker}
SESSION_SECRET={secrets.token_hex(40)}
APP_ORIGIN=http://localhost:8080
ENVIRONMENT=development
DEMO_AUTH=true
COOKIE_SECURE=false
OIDC_ISSUER=
OIDC_CLIENT_ID=maple-harbour
OIDC_CLIENT_SECRET=
''')
p.chmod(0o600)
print('Created local .env. Start: docker compose up --build -d')
