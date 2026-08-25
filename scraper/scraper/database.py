from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from scraper.config import REPO_ROOT, load_settings
from scraper.models import Base

_SYNC_ENGINE: Engine | None = None
_SYNC_SESSION_FACTORY: sessionmaker[Session] | None = None


def resolve_database_url(url: str) -> str:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    path = url[len(prefix):]
    if not path or path == ":memory:" or path.startswith("/"):
        return url
    return f"sqlite:///{REPO_ROOT / path}"


def get_engine() -> Engine:
    global _SYNC_ENGINE
    if _SYNC_ENGINE is None:
        settings = load_settings()
        url = resolve_database_url(settings.database_url)
        connect_args: dict[str, Any] = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _SYNC_ENGINE = create_engine(url, connect_args=connect_args, future=True)
    return _SYNC_ENGINE


def get_session_factory() -> sessionmaker[Session]:
    global _SYNC_SESSION_FACTORY
    if _SYNC_SESSION_FACTORY is None:
        _SYNC_SESSION_FACTORY = sessionmaker(
            bind=get_engine(), expire_on_commit=False, future=True
        )
    return _SYNC_SESSION_FACTORY


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    Base.metadata.create_all(get_engine())


def dispose_engine() -> None:
    global _SYNC_ENGINE, _SYNC_SESSION_FACTORY
    if _SYNC_ENGINE is not None:
        _SYNC_ENGINE.dispose()
    _SYNC_ENGINE = None
    _SYNC_SESSION_FACTORY = None
