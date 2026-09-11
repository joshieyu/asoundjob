from __future__ import annotations

import inspect
import re
import unittest
from pathlib import Path

from scraper.models import Base, Job
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.routers.jobs import list_jobs

REPO_ROOT = Path(__file__).resolve().parents[2]
JOBS_LOADER = REPO_ROOT / "web" / "src" / "routes" / "jobs" / "+page.server.ts"

LOADER_EXTRA_PARAMS = ("page", "per_page")


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_job(session, title: str, description: str) -> Job:
    job = Job(
        title=title,
        description=description,
        url=f"https://example.com/{title.lower().replace(' ', '-')}",
        is_active=True,
        is_audio_related=True,
    )
    session.add(job)
    session.flush()
    return job


def endpoint_defaults() -> dict:
    values = {}
    for name, param in inspect.signature(list_jobs).parameters.items():
        if name == "db":
            continue
        default = param.default
        if default is inspect.Parameter.empty:
            continue
        values[name] = getattr(default, "default", default)
    return values


def call_list_jobs(session, **kwargs):
    params = endpoint_defaults()
    params.update(kwargs)
    return list_jobs(db=session, **params)


def loader_api_param_names() -> set:
    source = JOBS_LOADER.read_text()

    allowed_block = re.search(r"const ALLOWED = \[(.*?)\]", source, re.S)
    assert allowed_block, "could not find ALLOWED in the jobs loader"
    allowed = set(re.findall(r"'([^']+)'", allowed_block.group(1)))

    aliases = {}
    alias_block = re.search(
        r"const API_PARAM_ALIASES[^=]*=\s*\{(.*?)\}", source, re.S
    )
    if alias_block:
        aliases = dict(re.findall(r"(\w+)\s*:\s*'([^']+)'", alias_block.group(1)))

    return {aliases.get(name, name) for name in allowed} | set(LOADER_EXTRA_PARAMS)


class TestJobSearchFiltering(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        make_job(self.session, "Mastering Engineer", "Master records for release.")
        make_job(self.session, "Audio DSP Engineer", "Write filters in C++.")
        make_job(self.session, "Live Sound Technician", "Mix front of house.")

    def tearDown(self) -> None:
        self.session.close()

    def test_search_reduces_result_count(self) -> None:
        unfiltered = call_list_jobs(self.session)
        filtered = call_list_jobs(self.session, search="mastering")

        self.assertEqual(unfiltered["total"], 3)
        self.assertEqual(filtered["total"], 1)
        self.assertLess(filtered["total"], unfiltered["total"])
        self.assertEqual(filtered["items"][0].title, "Mastering Engineer")

    def test_search_matches_description(self) -> None:
        filtered = call_list_jobs(self.session, search="front of house")
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(filtered["items"][0].title, "Live Sound Technician")

    def test_search_with_no_match_returns_nothing(self) -> None:
        self.assertEqual(call_list_jobs(self.session, search="zzzznope")["total"], 0)


class TestJobsLoaderParamContract(unittest.TestCase):
    def test_every_param_the_loader_sends_is_accepted(self) -> None:
        accepted = set(inspect.signature(list_jobs).parameters)
        for name in sorted(loader_api_param_names()):
            with self.subTest(param=name):
                self.assertIn(
                    name,
                    accepted,
                    f"the jobs loader sends '{name}', which /api/jobs silently ignores",
                )

    def test_search_is_the_name_sent_for_free_text(self) -> None:
        self.assertIn("search", loader_api_param_names())
        self.assertNotIn("q", loader_api_param_names())


if __name__ == "__main__":
    unittest.main()
