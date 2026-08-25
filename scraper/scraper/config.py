from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DATABASE_URL = "sqlite:///asoundjob.db"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    database_url: str
    data_dir: Path
    user_agent: str
    http_concurrency: int
    playwright_concurrency: int
    request_timeout: float
    page_load_timeout: float
    per_company_timeout: float


def load_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL
    return Settings(
        database_url=database_url,
        data_dir=Path(os.environ.get("DATA_DIR", str(REPO_ROOT / "data"))),
        user_agent=os.environ.get(
            "SCRAPER_USER_AGENT",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 ASoundJobBot/0.1",
        ),
        http_concurrency=_env_int("HTTP_CONCURRENCY", 50),
        playwright_concurrency=_env_int("PLAYWRIGHT_CONCURRENCY", 5),
        request_timeout=_env_float("REQUEST_TIMEOUT", 15.0),
        page_load_timeout=_env_float("PAGE_LOAD_TIMEOUT", 25.0),
        per_company_timeout=_env_float("PER_COMPANY_TIMEOUT", 90.0),
    )
