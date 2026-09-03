from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRAPER_DIR = REPO_ROOT / "scraper"

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "asoundjob-dev")
SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "dev-secret-change-me")
TOKEN_EXPIRE_MINUTES = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "720"))
ALGORITHM = "HS256"

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

SUBMISSIONS_PER_IP_PER_DAY = int(os.environ.get("SUBMISSIONS_PER_IP_PER_DAY", "3"))
COMMUNITY_JOB_TTL_DAYS = int(os.environ.get("COMMUNITY_JOB_TTL_DAYS", "30"))
MAX_COMMUNITY_JOB_DAYS = int(os.environ.get("MAX_COMMUNITY_JOB_DAYS", "365"))

DEFAULT_PER_PAGE = 25
MAX_PER_PAGE = 100
