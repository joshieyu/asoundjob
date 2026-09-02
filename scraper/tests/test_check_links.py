from __future__ import annotations

import unittest
from typing import Optional
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
    has_bad_links,
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


class TestClassifyWrongContent(unittest.TestCase):
    def test_workable_markdown_is_wrong_content(self) -> None:
        self.assertEqual(
            classify(
                200,
                "https://apply.workable.com/acme/jobs/view/abc",
                None,
                "text/markdown",
            ),
            "wrong_content",
        )

    def test_json_is_wrong_content(self) -> None:
        self.assertEqual(
            classify(200, "https://acme.example/jobs/1", None, "application/json"),
            "wrong_content",
        )

    def test_plain_text_is_wrong_content(self) -> None:
        self.assertEqual(
            classify(200, "https://acme.example/jobs/1", None, "text/plain"),
            "wrong_content",
        )

    def test_pdf_is_readable_and_ok(self) -> None:
        self.assertEqual(
            classify(200, "https://acme.example/jobs/1", None, "application/pdf"),
            "ok",
        )

    def test_html_is_ok(self) -> None:
        self.assertEqual(
            classify(200, "https://acme.example/jobs/1", None, "text/html"),
            "ok",
        )

    def test_html_with_charset_already_stripped_is_ok(self) -> None:
        self.assertEqual(
            classify(200, "https://acme.example/jobs/1", None, "text/html"),
            "ok",
        )

    def test_xhtml_is_ok(self) -> None:
        self.assertEqual(
            classify(200, "https://acme.example/jobs/1", None, "application/xhtml+xml"),
            "ok",
        )

    def test_missing_content_type_is_ok(self) -> None:
        self.assertEqual(
            classify(200, "https://acme.example/jobs/1", None, None), "ok"
        )

    def test_404_with_non_html_content_type_stays_broken(self) -> None:
        self.assertEqual(
            classify(404, "https://acme.example/jobs/1", None, "text/markdown"),
            "broken",
        )

    def test_500_with_non_html_content_type_stays_server_error(self) -> None:
        self.assertEqual(
            classify(500, "https://acme.example/jobs/1", None, "application/json"),
            "server_error",
        )

    def test_meta_whitelist_still_wins_over_content_type(self) -> None:
        self.assertEqual(
            classify(
                403,
                "https://www.metacareers.com/jobs/123",
                None,
                "application/json",
            ),
            "bot_defence",
        )


def make_check(
    url: str,
    company_name: str,
    title: str,
    bucket: str,
    job_id: int = 1,
    status=None,
    error=None,
    content_type: Optional[str] = None,
) -> UrlCheck:
    job = JobRef(job_id=job_id, url=url, title=title, company_name=company_name)
    return UrlCheck(
        url=url,
        jobs=[job],
        status=status,
        error=error,
        final_url=url,
        bucket=bucket,
        content_type=content_type,
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
            "ok", "broken", "wrong_content", "bot_defence", "server_error",
            "other_status", "error",
        ])
        self.assertEqual(counts["ok"], 1)
        self.assertEqual(counts["broken"], 2)
        self.assertEqual(counts["bot_defence"], 0)


class TestHasBadLinks(unittest.TestCase):
    def test_true_when_any_broken(self) -> None:
        report = LinkCheckReport(
            checks=[make_check("https://a.example/1", "Acme", "Engineer", "broken", status=404)]
        )
        self.assertTrue(has_bad_links(report))

    def test_true_when_any_wrong_content(self) -> None:
        report = LinkCheckReport(
            checks=[
                make_check(
                    "https://apply.workable.com/acme/jobs/view/abc",
                    "Acme",
                    "Engineer",
                    "wrong_content",
                    status=200,
                    content_type="text/markdown",
                )
            ]
        )
        self.assertTrue(has_bad_links(report))

    def test_false_when_none_broken(self) -> None:
        report = LinkCheckReport(
            checks=[make_check("https://a.example/1", "Acme", "Engineer", "ok", status=200)]
        )
        self.assertFalse(has_bad_links(report))


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
            make_check(
                "https://apply.workable.com/delta/jobs/view/xyz",
                "Delta",
                "Mixer",
                "wrong_content",
                job_id=10,
                status=200,
                content_type="text/markdown",
            ),
        ]
        return LinkCheckReport(checks=checks)

    def test_broken_company_appears_with_correct_counts(self) -> None:
        report = self._report()
        text = format_report(report, examples_limit=5)
        self.assertIn("total urls checked: 10", text)
        self.assertIn("total board rows covered: 10", text)
        self.assertIn("companies with broken links:", text)
        self.assertIn("Acme — 6 broken / 7 board rows", text)
        self.assertIn("Beta — 1 broken / 1 board rows", text)
        self.assertIn("companies with error:", text)
        self.assertIn("Gamma — 1", text)

    def test_wrong_content_company_appears_with_content_type_visible(self) -> None:
        report = self._report()
        text = format_report(report, examples_limit=5)
        self.assertIn("companies with wrong content type:", text)
        self.assertIn("Delta — 1 wrong content type / 1 board rows", text)
        self.assertIn(
            "Mixer -> https://apply.workable.com/delta/jobs/view/xyz [text/markdown]", text
        )

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

    def test_report_to_dict_wrong_content_companies_include_content_type(self) -> None:
        report = self._report()
        data = report_to_dict(report, examples_limit=5)
        delta_entry = next(
            entry for entry in data["wrong_content_companies"] if entry["company"] == "Delta"
        )
        self.assertEqual(delta_entry["wrong_content_count"], 1)
        self.assertEqual(delta_entry["total_board_rows"], 1)
        self.assertEqual(
            delta_entry["examples"],
            [
                {
                    "title": "Mixer",
                    "url": "https://apply.workable.com/delta/jobs/view/xyz",
                    "content_type": "text/markdown",
                }
            ],
        )

    def test_has_bad_links_true_for_wrong_content_only(self) -> None:
        report = LinkCheckReport(
            checks=[
                make_check(
                    "https://apply.workable.com/delta/jobs/view/xyz",
                    "Delta",
                    "Mixer",
                    "wrong_content",
                    status=200,
                    content_type="text/markdown",
                )
            ]
        )
        self.assertTrue(has_bad_links(report))


class FakeResponse:
    def __init__(
        self, status_code: int, url: str, headers: Optional[dict] = None
    ) -> None:
        self.status_code = status_code
        self.url = url
        self.headers = headers or {}

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
            [FakeResponse(404, url)],
            [FakeResponse(200, url, headers={"Content-Type": "text/html"})],
        )
        self.assertEqual(result, (200, None, url, "text/html"))
        self.assertEqual(session.get.call_count, 1)

    def test_head_200_with_html_skips_the_get(self) -> None:
        url = "https://acme.example/jobs/1"
        result, session = self._run(
            [FakeResponse(200, url, headers={"Content-Type": "text/html; charset=utf-8"})],
            [],
        )
        self.assertEqual(result, (200, None, url, "text/html"))
        self.assertEqual(session.get.call_count, 0)

    def test_head_200_with_no_content_type_triggers_get(self) -> None:
        url = "https://acme.example/jobs/1"
        result, session = self._run(
            [FakeResponse(200, url)],
            [FakeResponse(200, url, headers={"Content-Type": "text/html"})],
        )
        self.assertEqual(result, (200, None, url, "text/html"))
        self.assertEqual(session.get.call_count, 1)

    def test_head_200_with_markdown_triggers_get_and_uses_get_content_type(self) -> None:
        url = "https://apply.workable.com/acme/jobs/view/abc"
        result, session = self._run(
            [FakeResponse(200, url, headers={"Content-Type": "text/markdown"})],
            [FakeResponse(200, url, headers={"Content-Type": "text/markdown; charset=utf-8"})],
        )
        self.assertEqual(result, (200, None, url, "text/markdown"))
        self.assertEqual(session.get.call_count, 1)

    def test_get_confirms_a_real_404(self) -> None:
        url = "https://acme.example/jobs/gone"
        result, session = self._run(
            [FakeResponse(404, url)], [FakeResponse(404, url)]
        )
        self.assertEqual(result, (404, None, url, None))

    def test_head_raising_falls_back_to_get(self) -> None:
        url = "https://acme.example/jobs/1"
        result, _ = self._run(
            [requests.RequestException("boom")],
            [FakeResponse(200, url, headers={"Content-Type": "text/html"})],
        )
        self.assertEqual(result, (200, None, url, "text/html"))

    def test_both_failing_reports_the_transport_error(self) -> None:
        status, error, _final_url, content_type = self._run(
            [requests.RequestException("head boom")],
            [requests.RequestException("get boom")],
        )[0]
        self.assertIsNone(status)
        self.assertIsNone(content_type)
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
