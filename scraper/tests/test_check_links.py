from __future__ import annotations

import unittest
from unittest import mock

import requests

from scraper.check_links import (
    JobRef,
    LinkCheckReport,
    UrlCheck,
    _fetch_status,
    bucket_counts,
    classify,
    format_report,
    has_broken_links,
    parse_args,
    report_to_dict,
)


class TestClassifyOk(unittest.TestCase):
    def test_200_is_ok(self) -> None:
        self.assertEqual(classify(200, "https://acme.example/jobs/1", None), "ok")

    def test_204_is_ok(self) -> None:
        self.assertEqual(classify(204, "https://acme.example/jobs/1", None), "ok")

    def test_redirect_resolved_to_200_is_ok(self) -> None:
        self.assertEqual(classify(200, "https://acme.example/jobs/1-final", None), "ok")


class TestClassifyBroken(unittest.TestCase):
    def test_404_is_broken(self) -> None:
        self.assertEqual(classify(404, "https://acme.example/jobs/1", None), "broken")

    def test_410_is_broken(self) -> None:
        self.assertEqual(classify(410, "https://acme.example/jobs/1", None), "broken")


class TestClassifyBotDefence(unittest.TestCase):
    def test_403_is_bot_defence(self) -> None:
        self.assertEqual(classify(403, "https://acme.example/jobs/1", None), "bot_defence")

    def test_429_is_bot_defence(self) -> None:
        self.assertEqual(classify(429, "https://acme.example/jobs/1", None), "bot_defence")

    def test_999_is_bot_defence(self) -> None:
        self.assertEqual(classify(999, "https://acme.example/jobs/1", None), "bot_defence")


class TestClassifyServerError(unittest.TestCase):
    def test_500_is_server_error(self) -> None:
        self.assertEqual(classify(500, "https://acme.example/jobs/1", None), "server_error")

    def test_503_is_server_error(self) -> None:
        self.assertEqual(classify(503, "https://acme.example/jobs/1", None), "server_error")


class TestClassifyOtherStatus(unittest.TestCase):
    def test_418_is_other_status(self) -> None:
        self.assertEqual(classify(418, "https://acme.example/jobs/1", None), "other_status")


class TestClassifyError(unittest.TestCase):
    def test_transport_error_has_no_status(self) -> None:
        self.assertEqual(
            classify(None, "https://acme.example/jobs/1", "ConnectionError: refused"),
            "error",
        )


class TestClassifyMetaWhitelist(unittest.TestCase):
    def test_meta_400_is_bot_defence(self) -> None:
        self.assertEqual(
            classify(400, "https://www.metacareers.com/jobs/123", None), "bot_defence"
        )

    def test_meta_404_is_bot_defence_not_broken(self) -> None:
        self.assertEqual(
            classify(404, "https://www.metacareers.com/jobs/123", None), "bot_defence"
        )

    def test_meta_subdomain_is_bot_defence(self) -> None:
        self.assertEqual(
            classify(400, "https://jobs.metacareers.com/jobs/123", None), "bot_defence"
        )

    def test_non_whitelisted_host_400_is_other_status(self) -> None:
        self.assertEqual(
            classify(400, "https://acme.example/jobs/1", None), "other_status"
        )


def make_check(
    url: str,
    company_name: str,
    title: str,
    bucket: str,
    job_id: int = 1,
    status=None,
    error=None,
) -> UrlCheck:
    job = JobRef(job_id=job_id, url=url, title=title, company_name=company_name)
    return UrlCheck(
        url=url,
        jobs=[job],
        status=status,
        error=error,
        final_url=url,
        bucket=bucket,
    )


class TestBucketCounts(unittest.TestCase):
    def test_ordering_and_counts(self) -> None:
        report = LinkCheckReport(
            checks=[
                make_check("https://a.example/1", "Acme", "Engineer", "ok", status=200),
                make_check("https://a.example/2", "Acme", "Designer", "broken", status=404),
                make_check("https://b.example/1", "Beta", "Analyst", "broken", status=404),
            ]
        )
        counts = bucket_counts(report)
        self.assertEqual(list(counts.keys()), [
            "ok", "broken", "bot_defence", "server_error", "other_status", "error",
        ])
        self.assertEqual(counts["ok"], 1)
        self.assertEqual(counts["broken"], 2)
        self.assertEqual(counts["bot_defence"], 0)


class TestHasBrokenLinks(unittest.TestCase):
    def test_true_when_any_broken(self) -> None:
        report = LinkCheckReport(
            checks=[make_check("https://a.example/1", "Acme", "Engineer", "broken", status=404)]
        )
        self.assertTrue(has_broken_links(report))

    def test_false_when_none_broken(self) -> None:
        report = LinkCheckReport(
            checks=[make_check("https://a.example/1", "Acme", "Engineer", "ok", status=200)]
        )
        self.assertFalse(has_broken_links(report))


class TestFormatReport(unittest.TestCase):
    def _report(self) -> LinkCheckReport:
        checks = [
            make_check("https://a.example/1", "Acme", "Engineer", "ok", job_id=1, status=200),
            make_check("https://a.example/2", "Acme", "Designer", "broken", job_id=2, status=404),
            make_check("https://a.example/3", "Acme", "Manager", "broken", job_id=3, status=404),
            make_check("https://a.example/4", "Acme", "Cook", "broken", job_id=4, status=404),
            make_check("https://a.example/5", "Acme", "Chef", "broken", job_id=5, status=404),
            make_check("https://a.example/6", "Acme", "Baker", "broken", job_id=6, status=404),
            make_check("https://a.example/7", "Acme", "Barber", "broken", job_id=7, status=404),
            make_check("https://b.example/1", "Beta", "Analyst", "broken", job_id=8, status=404),
            make_check(
                "https://c.example/1",
                "Gamma",
                "Roadie",
                "error",
                job_id=9,
                error="ConnectionError",
            ),
        ]
        return LinkCheckReport(checks=checks)

    def test_broken_company_appears_with_correct_counts(self) -> None:
        report = self._report()
        text = format_report(report, examples_limit=5)
        self.assertIn("total urls checked: 9", text)
        self.assertIn("total board rows covered: 9", text)
        self.assertIn("companies with broken links:", text)
        self.assertIn("Acme — 6 broken / 7 board rows", text)
        self.assertIn("Beta — 1 broken / 1 board rows", text)
        self.assertIn("companies with error:", text)
        self.assertIn("Gamma — 1", text)

    def test_examples_honour_limit(self) -> None:
        report = self._report()
        text = format_report(report, examples_limit=2)
        acme_lines = [line for line in text.splitlines() if "->" in line]
        acme_example_lines = [
            line for line in acme_lines if "Designer" in line or "Manager" in line
            or "Cook" in line or "Chef" in line or "Baker" in line or "Barber" in line
        ]
        self.assertEqual(len(acme_example_lines), 2)

    def test_report_to_dict_examples_honour_limit(self) -> None:
        report = self._report()
        data = report_to_dict(report, examples_limit=2)
        acme_entry = next(
            entry for entry in data["broken_companies"] if entry["company"] == "Acme"
        )
        self.assertEqual(acme_entry["broken_count"], 6)
        self.assertEqual(acme_entry["total_board_rows"], 7)
        self.assertEqual(len(acme_entry["examples"]), 2)


class FakeResponse:
    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url

    def close(self) -> None:
        return None


class TestFetchStatusFallsBackToGet(unittest.TestCase):
    def _run(self, head, get):
        session = mock.Mock()
        session.head.side_effect = head
        session.get.side_effect = get
        settings = mock.Mock(request_timeout=5.0)
        with mock.patch("scraper.check_links._get_session", return_value=session):
            return _fetch_status("https://acme.example/en/postings/abc", settings), session

    def test_head_404_is_reverified_with_get(self) -> None:
        url = "https://acme.example/en/postings/abc"
        result, session = self._run(
            [FakeResponse(404, url)], [FakeResponse(200, url)]
        )
        self.assertEqual(result, (200, None, url))
        self.assertEqual(session.get.call_count, 1)

    def test_head_200_skips_the_get(self) -> None:
        url = "https://acme.example/jobs/1"
        result, session = self._run([FakeResponse(200, url)], [])
        self.assertEqual(result, (200, None, url))
        self.assertEqual(session.get.call_count, 0)

    def test_get_confirms_a_real_404(self) -> None:
        url = "https://acme.example/jobs/gone"
        result, session = self._run(
            [FakeResponse(404, url)], [FakeResponse(404, url)]
        )
        self.assertEqual(result, (404, None, url))

    def test_head_raising_falls_back_to_get(self) -> None:
        url = "https://acme.example/jobs/1"
        result, _ = self._run(
            [requests.RequestException("boom")], [FakeResponse(200, url)]
        )
        self.assertEqual(result, (200, None, url))

    def test_both_failing_reports_the_transport_error(self) -> None:
        status, error, _ = self._run(
            [requests.RequestException("head boom")],
            [requests.RequestException("get boom")],
        )[0]
        self.assertIsNone(status)
        self.assertIn("get boom", error or "")


class TestParseArgs(unittest.TestCase):
    def test_defaults(self) -> None:
        args = parse_args([])
        self.assertFalse(args.all)
        self.assertIsNone(args.company)
        self.assertIsNone(args.limit)
        self.assertEqual(args.examples, 5)
        self.assertFalse(args.json)

    def test_all_options(self) -> None:
        args = parse_args(
            ["--all", "--company", "acme", "--limit", "10", "--examples", "3", "--json"]
        )
        self.assertTrue(args.all)
        self.assertEqual(args.company, "acme")
        self.assertEqual(args.limit, 10)
        self.assertEqual(args.examples, 3)
        self.assertTrue(args.json)


if __name__ == "__main__":
    unittest.main()
