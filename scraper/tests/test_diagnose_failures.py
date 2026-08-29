from __future__ import annotations

import unittest

from scraper.diagnose_failures import PageProbe, classify, summarize

BASE_KWARGS = {"company_id": 1, "company_name": "Acme", "url": "https://acme.example.com/careers"}


def make_probe(**overrides) -> PageProbe:
    kwargs = dict(BASE_KWARGS)
    kwargs.update(overrides)
    return PageProbe(**kwargs)


class TestClassifyUnreachable(unittest.TestCase):
    def test_cert_error(self) -> None:
        probe = make_probe(error="net::ERR_CERT_AUTHORITY_INVALID")
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "unreachable")
        self.assertTrue(detail.startswith("tls: "))

    def test_dns_error(self) -> None:
        probe = make_probe(error="net::ERR_NAME_NOT_RESOLVED")
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "unreachable")
        self.assertEqual(detail, "dns")

    def test_cert_and_dns_have_different_details(self) -> None:
        cert_probe = make_probe(error="SSL handshake failed")
        dns_probe = make_probe(error="getaddrinfo ENOTFOUND acme.example.com")
        cert_bucket, cert_detail = classify(cert_probe)
        dns_bucket, dns_detail = classify(dns_probe)
        self.assertEqual(cert_bucket, "unreachable")
        self.assertEqual(dns_bucket, "unreachable")
        self.assertNotEqual(cert_detail, dns_detail)

    def test_timeout_error(self) -> None:
        probe = make_probe(error="Timeout 25000ms exceeded")
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "unreachable")
        self.assertEqual(detail, "timeout")

    def test_generic_error_falls_back_to_short_message(self) -> None:
        probe = make_probe(error="something unexpected broke")
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "unreachable")
        self.assertEqual(detail, "something unexpected broke")


class TestClassifyHttpStatus(unittest.TestCase):
    def test_403_is_blocked(self) -> None:
        probe = make_probe(status=403)
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "blocked")
        self.assertEqual(detail, "http 403")

    def test_401_is_blocked(self) -> None:
        probe = make_probe(status=401)
        bucket, _detail = classify(probe)
        self.assertEqual(bucket, "blocked")

    def test_429_is_blocked(self) -> None:
        probe = make_probe(status=429)
        bucket, _detail = classify(probe)
        self.assertEqual(bucket, "blocked")

    def test_404_is_dead_url(self) -> None:
        probe = make_probe(status=404)
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "dead_url")
        self.assertEqual(detail, "http 404")

    def test_500_is_dead_url(self) -> None:
        probe = make_probe(status=500)
        bucket, _detail = classify(probe)
        self.assertEqual(bucket, "dead_url")


class TestClassifyBlockedInterstitial(unittest.TestCase):
    def test_cloudflare_interstitial(self) -> None:
        html = """
        <html><head><title>Just a moment...</title></head>
        <body>Checking your browser before accessing acme.example.com.
        Cloudflare Ray ID: 8f3a</body></html>
        """
        probe = make_probe(status=200, html=html)
        bucket, _detail = classify(probe)
        self.assertEqual(bucket, "blocked")


class TestClassifyAtsDiscoverable(unittest.TestCase):
    def test_greenhouse_embed_is_discoverable(self) -> None:
        html = """
        <html><body>
        <iframe src="https://boards.greenhouse.io/acme"></iframe>
        </body></html>
        """
        probe = make_probe(status=200, html=html)
        bucket, detail = classify(probe)
        self.assertEqual((bucket, detail), ("ats_discoverable", "greenhouse"))

    def test_discoverable_ats_in_links_only(self) -> None:
        probe = make_probe(
            status=200,
            html="<html><body>Careers at Acme</body></html>",
            links=["https://jobs.lever.co/acme-inc"],
        )
        bucket, detail = classify(probe)
        self.assertEqual((bucket, detail), ("ats_discoverable", "lever"))

    def test_ats_discoverable_takes_priority_over_no_openings(self) -> None:
        html = """
        <html><body>
        <iframe src="https://boards.greenhouse.io/acme"></iframe>
        <p>There are currently no open positions at this time.</p>
        </body></html>
        """
        probe = make_probe(status=200, html=html)
        bucket, detail = classify(probe)
        self.assertEqual((bucket, detail), ("ats_discoverable", "greenhouse"))


class TestClassifyAtsUnsupported(unittest.TestCase):
    def test_jobvite_link(self) -> None:
        html = """
        <html><body>
        <a href="https://jobs.jobvite.com/acme">See open roles</a>
        </body></html>
        """
        probe = make_probe(status=200, html=html)
        bucket, detail = classify(probe)
        self.assertEqual((bucket, detail), ("ats_unsupported", "jobvite"))


class TestClassifyJsonEndpoint(unittest.TestCase):
    def test_json_endpoint_present(self) -> None:
        probe = make_probe(
            status=200,
            html="<html><body>Careers at Acme</body></html>",
            json_endpoints=["https://acme.example.com/api/jobs?page=1"],
        )
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "json_endpoint")
        self.assertIn("jobs", detail)


class TestClassifyNoOpenings(unittest.TestCase):
    def test_currently_no_open_positions(self) -> None:
        html = """
        <html><body>
        <h1>Careers</h1>
        <p>There are currently no open positions at Acme. Please check back soon.</p>
        </body></html>
        """
        probe = make_probe(status=200, html=html)
        bucket, _detail = classify(probe)
        self.assertEqual(bucket, "no_openings")


class TestClassifyNotCareersPage(unittest.TestCase):
    def test_loudspeaker_product_page(self) -> None:
        html = """
        <html><body>
        <h1>Acme Loudspeakers</h1>
        <p>Our latest passive monitor delivers pristine, transparent sound
        for the studio and the stage. Available in three cabinet finishes.</p>
        </body></html>
        """
        probe = make_probe(status=200, html=html)
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "not_a_careers_page")
        self.assertEqual(detail, "no careers vocabulary")


class TestClassifyExtractorGap(unittest.TestCase):
    def test_links_extracted_but_none_reported(self) -> None:
        html = "<html><body><h1>Careers at Acme</h1></body></html>"
        probe = make_probe(status=200, html=html, job_link_count=7)
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "extractor_gap")
        self.assertIn("7", detail)


class TestClassifyJsRendered(unittest.TestCase):
    def test_bare_react_shell(self) -> None:
        html = """
        <html><body>
        <h1>Careers</h1>
        <div id="root"></div>
        <script src="/static/bundle.js"></script>
        </body></html>
        """
        probe = make_probe(status=200, html=html, job_link_count=0)
        bucket, _detail = classify(probe)
        self.assertEqual(bucket, "js_rendered")


class TestClassifyUnknown(unittest.TestCase):
    def test_empty_ish_page_with_careers_vocabulary(self) -> None:
        html = "<html><body><h1>Careers at Acme</h1></body></html>"
        probe = make_probe(status=200, html=html, job_link_count=0)
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "unknown")
        self.assertEqual(detail, "")


class TestSummarize(unittest.TestCase):
    def test_orders_by_count_descending(self) -> None:
        results = [
            ("blocked", "http 403"),
            ("no_openings", "check back"),
            ("blocked", "cloudflare"),
            ("unknown", ""),
            ("blocked", "http 429"),
            ("no_openings", "no vacancies"),
        ]
        summary = summarize(results)
        self.assertEqual(list(summary.keys()), ["blocked", "no_openings", "unknown"])
        self.assertEqual(summary["blocked"], 3)
        self.assertEqual(summary["no_openings"], 2)
        self.assertEqual(summary["unknown"], 1)

    def test_empty_input(self) -> None:
        self.assertEqual(summarize([]), {})


if __name__ == "__main__":
    unittest.main()
