from __future__ import annotations

import json
import threading
from datetime import date, datetime, timezone
from typing import Any

import requests  # type: ignore[import-untyped]

from scraper.config import Settings

_LOCAL = threading.local()


def _get_session(settings: Settings) -> requests.Session:
    session = getattr(_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": settings.user_agent,
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        _LOCAL.session = session
    return session


class FetchError(Exception):
    pass


def fetch_json(url: str, settings: Settings, timeout: float | None = None) -> Any:
    response = _get_session(settings).get(
        url, timeout=timeout or settings.request_timeout
    )
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code} for {url}")
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise FetchError(f"Invalid JSON from {url}: {exc}") from exc


def post_json(
    url: str, payload: Any, settings: Settings, timeout: float | None = None
) -> Any:
    response = _get_session(settings).post(
        url, json=payload, timeout=timeout or settings.request_timeout
    )
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code} for {url}")
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise FetchError(f"Invalid JSON from {url}: {exc}") from exc


def fetch_html(url: str, settings: Settings, timeout: float | None = None) -> str:
    response = _get_session(settings).get(
        url, timeout=timeout or settings.request_timeout
    )
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code} for {url}")
    return response.text


def parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(ts, tz=timezone.utc).date()
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None
