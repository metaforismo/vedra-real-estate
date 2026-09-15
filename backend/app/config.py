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
    seed_demo: bool = field(default_factory=lambda: flag("SEED_DEMO", "true"))
    scheduler: bool = field(default_factory=lambda: flag("SCHEDULER_ENABLED", "true"))
    allowed_hosts: list[str] = field(default_factory=lambda: os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(","))
    public_origin: str = field(default_factory=lambda: os.getenv("PUBLIC_ORIGIN", "http://localhost:8000").rstrip("/"))
    live_domains: list[str] = field(default_factory=lambda: [x.strip().lower() for x in os.getenv("LIVE_ALLOWED_DOMAINS", "").split(",") if x.strip()])
    browser_enabled: bool = field(default_factory=lambda: flag("BROWSER_ENABLED"))
    hermes_url: str = field(default_factory=lambda: os.getenv("HERMES_BASE_URL", "http://127.0.0.1:8642").rstrip("/"))
    hermes_key: str = field(default_factory=lambda: os.getenv("HERMES_API_KEY", ""))
    bridge_token: str = field(default_factory=lambda: os.getenv("VEDRA_BRIDGE_TOKEN", ""))
    hermes_timeout: int = field(default_factory=lambda: int(os.getenv("HERMES_TIMEOUT_SECONDS", "480")))
    max_html_bytes: int = 3_000_000
    max_import_bytes: int = 4_000_000
    session_hours: int = 12
    request_delay: float = 2.0
    root: Path = ROOT

    @property
    def db_path(self) -> Path:
        return self.data_dir / "vedra.sqlite3"
