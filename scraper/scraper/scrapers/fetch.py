from __future__ import annotations

import json
import threading
from datetime import date, datetime, timezone
from typing import Any, Callable, TypeVar
from urllib.parse import parse_qs, urlsplit

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


TIMEOUT_RETRIES = 1
T = TypeVar("T")


def retry_on_timeout(call: Callable[[], T]) -> T:
    for attempt in range(TIMEOUT_RETRIES + 1):
        try:
            return call()
        except requests.Timeout:
            if attempt >= TIMEOUT_RETRIES:
                raise
    raise AssertionError("unreachable")


def _send(
    method: str, url: str, settings: Settings, timeout: float | None, **kwargs: Any
) -> requests.Response:
    session = _get_session(settings)
    return retry_on_timeout(
        lambda: session.request(
            method, url, timeout=timeout or settings.request_timeout, **kwargs
        )
    )


class FetchError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def fetch_json(url: str, settings: Settings, timeout: float | None = None) -> Any:
    response = _send("GET", url, settings, timeout)
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code} for {url}", response.status_code)
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise FetchError(f"Invalid JSON from {url}: {exc}") from exc


def post_json(
    url: str, payload: Any, settings: Settings, timeout: float | None = None
) -> Any:
    response = _send("POST", url, settings, timeout, json=payload)
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code} for {url}", response.status_code)
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise FetchError(f"Invalid JSON from {url}: {exc}") from exc


def fetch_page(
    url: str, settings: Settings, timeout: float | None = None
) -> tuple[str, str]:
    response = _send("GET", url, settings, timeout)
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code} for {url}", response.status_code)
    return response.text, str(response.url or url)


def fetch_html(url: str, settings: Settings, timeout: float | None = None) -> str:
    response = _send("GET", url, settings, timeout)
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code} for {url}", response.status_code)
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


def extract_query(url: str) -> str:
    parsed = urlsplit((url or "").strip())
    values = parse_qs(parsed.query).get("q")
    return values[0] if values else ""
