from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_env(path: Path = ROOT / ".env") -> None:
    """Small .env reader: literal values only, never evaluates shell expressions."""
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def data_directory() -> Path:
    path = Path(os.getenv("DATA_DIR", str(ROOT / "data"))).expanduser()
    return path if path.is_absolute() else ROOT / path


def flag(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).lower() in {"1", "true", "yes"}


@dataclass
class Settings:
    data_dir: Path = field(default_factory=data_directory)
    admin_email: str = field(default_factory=lambda: os.getenv("ADMIN_EMAIL", "admin@vedra.local"))
    admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", ""))
    cookie_secure: bool = field(default_factory=lambda: flag("COOKIE_SECURE"))
    database_url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', ''))
    database_schema: str = field(default_factory=lambda: os.getenv('DATABASE_SCHEMA', 'vedra'))
    database_pool_size: int = field(default_factory=lambda: int(os.getenv('DATABASE_POOL_SIZE', '4')))
    worker_enabled: bool = field(default_factory=lambda: flag('WORKER_ENABLED', 'true'))
    image_domains: list[str] = field(default_factory=lambda: [x.strip().lower() for x in os.getenv('IMAGE_ALLOWED_DOMAINS', '').split(',') if x.strip()])
    omi_enabled: bool = field(default_factory=lambda: flag('OMI_ENABLED'))
    scheduler: bool = field(default_factory=lambda: flag("SCHEDULER_ENABLED", "true"))
    allowed_hosts: list[str] = field(default_factory=lambda: os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(","))
    public_origin: str = field(default_factory=lambda: os.getenv("PUBLIC_ORIGIN", "http://localhost:8000").rstrip("/"))
    live_domains: list[str] = field(default_factory=lambda: [x.strip().lower() for x in os.getenv("LIVE_ALLOWED_DOMAINS", "").split(",") if x.strip()])
    browser_enabled: bool = field(default_factory=lambda: flag("BROWSER_ENABLED"))
    browser_executable: str = field(default_factory=lambda: os.getenv('BROWSER_EXECUTABLE_PATH', ''))
    hermes_url: str = field(default_factory=lambda: os.getenv("HERMES_BASE_URL", "http://127.0.0.1:8642").rstrip("/"))
    hermes_key: str = field(default_factory=lambda: os.getenv("HERMES_API_KEY", ""))
    bridge_token: str = field(default_factory=lambda: os.getenv("VEDRA_BRIDGE_TOKEN", ""))
    hermes_timeout: int = field(default_factory=lambda: int(os.getenv("HERMES_TIMEOUT_SECONDS", "480")))
    max_html_bytes: int = 3_000_000
    max_import_bytes: int = 4_000_000
    session_hours: int = 12
    request_delay: float = 2.0
    root: Path = ROOT

    workspace_name: str = field(default_factory=lambda: os.getenv("WORKSPACE_NAME", "Investment workspace"))
    workspace_id: str = field(default_factory=lambda: os.getenv("WORKSPACE_ID", "default"))
    run_timeout: int = field(default_factory=lambda: int(os.getenv("RUN_TIMEOUT_SECONDS", "900")))
    max_ai_listings: int = field(default_factory=lambda: int(os.getenv("AI_MAX_ANALYSES_PER_RUN", "30")))
    ai_url: str = field(default_factory=lambda: os.getenv("AI_API_BASE_URL", "").rstrip("/"))
    ai_key: str = field(default_factory=lambda: os.getenv("AI_API_KEY", ""))
    ai_model: str = field(default_factory=lambda: os.getenv("AI_MODEL", ""))
    ai_reasoning: str = field(default_factory=lambda: os.getenv("AI_REASONING_EFFORT", ""))
    ai_format: str = field(default_factory=lambda: os.getenv("AI_RESPONSE_FORMAT", "json_object"))
    ai_timeout: float = field(default_factory=lambda: float(os.getenv("AI_TIMEOUT_SECONDS", "90")))
    ai_max_tokens: int = field(default_factory=lambda: int(os.getenv("AI_MAX_OUTPUT_TOKENS", "2000")))
    ai_input_price: float | None = field(default_factory=lambda: float(os.environ['AI_INPUT_EUR_PER_MILLION']) if os.getenv('AI_INPUT_EUR_PER_MILLION') else None)
    ai_output_price: float | None = field(default_factory=lambda: float(os.environ['AI_OUTPUT_EUR_PER_MILLION']) if os.getenv('AI_OUTPUT_EUR_PER_MILLION') else None)
    hermes_mcp_only: bool = True
    mail_enabled: bool = field(default_factory=lambda: flag('MAIL_ENABLED'))
    smtp_host: str = field(default_factory=lambda: os.getenv('SMTP_HOST', ''))
    smtp_port: int = field(default_factory=lambda: int(os.getenv('SMTP_PORT', '587')))
    smtp_user: str = field(default_factory=lambda: os.getenv('SMTP_USER', ''))
    smtp_password: str = field(default_factory=lambda: os.getenv('SMTP_PASSWORD', ''))
    smtp_from: str = field(default_factory=lambda: os.getenv('SMTP_FROM', ''))
    smtp_recipients: list[str] = field(default_factory=lambda: [x.strip() for x in os.getenv('SMTP_TO', '').split(',') if x.strip()])
    smtp_tls: bool = field(default_factory=lambda: flag('SMTP_STARTTLS', 'true'))

    def __post_init__(self):
        import math
        from urllib.parse import urlsplit
        if not 2 <= self.database_pool_size <= 16:
            raise ValueError('DATABASE_POOL_SIZE deve essere tra 2 e 16.')
        if self.database_url:
            u = urlsplit(self.database_url)
            if u.scheme not in ('postgresql', 'postgres') or not u.hostname:
                raise ValueError('DATABASE_URL deve essere una connessione PostgreSQL.')
            if u.port == 6543:
                raise ValueError('Usa la connessione diretta o il session pooler, non transaction mode (6543).')
        if not 5 <= self.run_timeout <= 86400 or not 1 <= self.max_ai_listings <= 100:
            raise ValueError('Budget run non valido.')
        if not math.isfinite(self.ai_timeout) or not 1 <= self.ai_timeout <= 900:
            raise ValueError('AI_TIMEOUT_SECONDS deve essere tra 1 e 900.')
        if not 128 <= self.ai_max_tokens <= 32000:
            raise ValueError('AI_MAX_OUTPUT_TOKENS fuori limite.')
        if self.ai_format not in ('json_object', 'json_schema', 'none'):
            raise ValueError('AI_RESPONSE_FORMAT non valido.')
        if self.ai_reasoning not in ('', 'none','minimal','low','medium','high','xhigh'):
            raise ValueError('AI_REASONING_EFFORT non valido.')
        for price in (self.ai_input_price,self.ai_output_price):
            if price is not None and (not math.isfinite(price) or price < 0):
                raise ValueError('Tariffa AI non valida.')
        if self.ai_url:
            u=urlsplit(self.ai_url)
            if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.query or u.fragment:
                raise ValueError('AI_API_BASE_URL non valida.')
            if u.scheme=='http' and u.hostname not in ('localhost','127.0.0.1','::1'):
                raise ValueError('Il provider remoto deve usare HTTPS.')
        if self.mail_enabled and (not self.smtp_host or not self.smtp_from or not self.smtp_recipients):
            raise ValueError('Configura SMTP_HOST, SMTP_FROM e SMTP_TO prima di attivare le email.')
        if any('\n' in x or '\r' in x for x in [self.smtp_from,*self.smtp_recipients]):
            raise ValueError('Indirizzo email non valido.')

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_url and self.ai_model and self.ai_key)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "vedra.sqlite3"
