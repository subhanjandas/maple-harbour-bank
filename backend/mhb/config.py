import os
from dataclasses import dataclass

@dataclass
class Settings:
    database_url: str = os.getenv('DATABASE_URL', '')
    worker_database_url: str = os.getenv('WORKER_DATABASE_URL', '')
    environment: str = os.getenv('ENVIRONMENT', 'development')
    demo_auth: bool = os.getenv('DEMO_AUTH', 'false').lower() == 'true'
    origin: str = os.getenv('APP_ORIGIN', 'http://localhost:8080')
    session_secret: str = os.getenv('SESSION_SECRET', '')
    oidc_issuer: str = os.getenv('OIDC_ISSUER', '')
    oidc_client_id: str = os.getenv('OIDC_CLIENT_ID', 'maple-harbour')
    oidc_client_secret: str = os.getenv('OIDC_CLIENT_SECRET', '')
    secure_cookies: bool = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
    request_limit: int = int(os.getenv('REQUEST_LIMIT_PER_MINUTE', '120'))

    def validate(self):
        if not self.database_url or len(self.session_secret) < 32:
            raise RuntimeError('DATABASE_URL and a random SESSION_SECRET (32+ characters) are required')
        if self.environment != 'development':
            if self.demo_auth or not self.secure_cookies or not self.origin.startswith('https://') or not self.oidc_issuer.startswith('https://'):
                raise RuntimeError('Hosted runtime requires HTTPS OIDC, secure cookies and DEMO_AUTH=false')
