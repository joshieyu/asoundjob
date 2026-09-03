from __future__ import annotations

import unittest

from scraper.config import REPO_ROOT
from scraper.database import resolve_database_url


class TestResolveDatabaseUrl(unittest.TestCase):
    def test_relative_sqlite_path_anchors_to_repo_root(self) -> None:
        resolved = resolve_database_url("sqlite:///asoundjob.db")
        self.assertEqual(resolved, f"sqlite:///{REPO_ROOT / 'asoundjob.db'}")

    def test_absolute_sqlite_path_is_left_alone(self) -> None:
        self.assertEqual(
            resolve_database_url("sqlite:////var/tmp/x.db"),
            "sqlite:////var/tmp/x.db",
        )

    def test_memory_database_is_left_alone(self) -> None:
        self.assertEqual(
            resolve_database_url("sqlite:///:memory:"), "sqlite:///:memory:"
        )

    def test_non_sqlite_url_is_left_alone(self) -> None:
        url = "postgresql+psycopg://user@host/db"
        self.assertEqual(resolve_database_url(url), url)


if __name__ == "__main__":
    unittest.main()
