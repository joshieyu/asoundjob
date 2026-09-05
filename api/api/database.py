from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from scraper.database import get_session_factory, init_db


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = ["get_db", "init_db"]
