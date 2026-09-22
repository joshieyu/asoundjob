from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRAPER_DIR = REPO_ROOT / "scraper"

DEV_ADMIN_PASSWORD = "asoundjob-dev"
DEV_SECRET_KEY = "dev-secret-change-me"

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", DEV_ADMIN_PASSWORD)
SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", DEV_SECRET_KEY)
TOKEN_EXPIRE_MINUTES = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "720"))
ALGORITHM = "HS256"

MIN_ADMIN_PASSWORD_LENGTH = 12
MIN_SECRET_KEY_LENGTH = 32

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


def production_config_errors(env: Mapping[str, str]) -> list[str]:
    if env.get("ASOUNDJOB_ENV", "").strip().lower() != "production":
        return []

    errors: list[str] = []

    admin_password = env.get("ADMIN_PASSWORD", "")
    if not admin_password:
        errors.append("ADMIN_PASSWORD is unset or blank")
    elif admin_password == DEV_ADMIN_PASSWORD:
        errors.append("ADMIN_PASSWORD is the development default")
    elif len(admin_password) < MIN_ADMIN_PASSWORD_LENGTH:
        errors.append(f"ADMIN_PASSWORD is shorter than {MIN_ADMIN_PASSWORD_LENGTH} characters")

    secret_key = env.get("ADMIN_SECRET_KEY", "")
    if not secret_key:
        errors.append("ADMIN_SECRET_KEY is unset or blank")
    elif secret_key == DEV_SECRET_KEY:
        errors.append("ADMIN_SECRET_KEY is the development default")
    elif len(secret_key) < MIN_SECRET_KEY_LENGTH:
        errors.append(f"ADMIN_SECRET_KEY is shorter than {MIN_SECRET_KEY_LENGTH} characters")

    return errors


def dev_credentials_in_use(env: Mapping[str, str]) -> bool:
    if env.get("ASOUNDJOB_ENV", "").strip().lower() == "production":
        return False

    admin_password = env.get("ADMIN_PASSWORD", "")
    secret_key = env.get("ADMIN_SECRET_KEY", "")

    password_is_dev = not admin_password or admin_password == DEV_ADMIN_PASSWORD
    secret_is_dev = not secret_key or secret_key == DEV_SECRET_KEY

    return password_is_dev or secret_is_dev
