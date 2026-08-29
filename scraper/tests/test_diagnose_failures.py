from __future__ import annotations

import time
import unittest
from dataclasses import asdict

from scraper.diagnose_failures import (
    PageProbe,
    classify,
    is_job_endpoint,
    probe_from_dict,
    summarize,
)

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

    def test_small_challenge_platform_page_is_blocked(self) -> None:
        html = "<html><body>" + ("x" * 400) + "/cdn-cgi/challenge-platform" + "</body></html>"
        self.assertLess(len(html), 20000)
        probe = make_probe(status=200, html=html)
        bucket, _detail = classify(probe)
        self.assertEqual(bucket, "blocked")

    def test_large_page_with_just_a_moment_is_not_blocked(self) -> None:
        html = "<html><body>just a moment...</body></html>" + ("z" * 50000)
        self.assertGreaterEqual(len(html), 50000)
        probe = make_probe(status=200, html=html)
        bucket, _detail = classify(probe)
        self.assertNotEqual(bucket, "blocked")

    def test_normal_page_with_cloudflare_word_is_not_blocked(self) -> None:
        html = (
            "<html><body><h1>Careers at Acme</h1>"
            "<p>We build studio monitors and stage gear. Join our team.</p>"
            '<script data-cfasync="false" src="/cdn-cgi/l/email-protection">'
            "[cloudflare email protection]</script>"
            + ("<!-- padding -->" * 2000)
            + "</body></html>"
        )
        self.assertGreaterEqual(len(html), 30000)
        probe = make_probe(status=200, html=html)
        bucket, _detail = classify(probe)
        self.assertNotEqual(bucket, "blocked")

    def test_recaptcha_widget_on_contact_form_is_not_blocked(self) -> None:
        html = """
        <html><body>
        <h1>Careers at Acme</h1>
        <p>See our open roles below and get in touch with recruiting.</p>
        <form>
        <div class="g-recaptcha" data-sitekey="abc123"></div>
        <script src="https://www.google.com/recaptcha/api.js"></script>
        </form>
        </body></html>
        """
        probe = make_probe(status=200, html=html)
        bucket, _detail = classify(probe)
        self.assertNotEqual(bucket, "blocked")


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

    def test_only_noise_endpoints_falls_through(self) -> None:
        probe = make_probe(
            status=200,
            html="<html><body><h1>Careers at Acme</h1></body></html>",
            json_endpoints=["https://cdn.cookielaw.org/consent/abc/otBannerSdk.js"],
        )
        bucket, _detail = classify(probe)
        self.assertNotEqual(bucket, "json_endpoint")
        self.assertEqual(bucket, "unknown")


class TestIsJobEndpoint(unittest.TestCase):
    PAGE_URL = "https://acme.example.com/careers"

    def test_cookielaw_is_noise(self) -> None:
        self.assertFalse(
            is_job_endpoint(
                self.PAGE_URL,
                "https://cdn.cookielaw.org/consent/abc/otBannerSdk.js",
            )
        )

    def test_youtube_is_noise(self) -> None:
        self.assertFalse(is_job_endpoint(self.PAGE_URL, "https://www.youtube.com/iframe_api"))

    def test_job_vocabulary_in_path(self) -> None:
        self.assertTrue(
            is_job_endpoint(
                "https://anghami.com/careers",
                "https://anghami.zenats.com/en/api/v1/career_page/live?slug=x",
            )
        )

    def test_jobs_json_path(self) -> None:
        self.assertTrue(
            is_job_endpoint(
                "https://www.annapurna.com/careers",
                "https://www.annapurna.com/_next/data/abc/jobs.json",
            )
        )

    def test_same_host_with_no_job_vocabulary_is_true(self) -> None:
        self.assertTrue(
            is_job_endpoint(
                self.PAGE_URL,
                "https://acme.example.com/api/data.json",
            )
        )

    def test_unrelated_third_party_with_no_job_vocabulary_is_false(self) -> None:
        self.assertFalse(
            is_job_endpoint(
                self.PAGE_URL,
                "https://random-vendor.io/api/data.json",
            )
        )


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

    def test_wordpress_page_is_not_js_rendered(self) -> None:
        html = """
        <html><body>
        <h1>Careers at Acme</h1>
        <link rel="stylesheet" href="/wp-content/plugins/some-plugin/style.css">
        <p>We build studio monitors and stage gear. Join our team.</p>
        </body></html>
        """
        probe = make_probe(status=200, html=html, job_link_count=0)
        bucket, _detail = classify(probe)
        self.assertNotEqual(bucket, "js_rendered")
        self.assertEqual(bucket, "unknown")


class TestClassifyCaptchaRedirect(unittest.TestCase):
    def test_sgcaptcha_final_url_is_blocked(self) -> None:
        probe = make_probe(
            status=200,
            html="<html><body>Careers</body></html>",
            final_url="https://acme.example.com/.well-known/sgcaptcha/?r=%2Fcareers",
        )
        bucket, detail = classify(probe)
        self.assertEqual((bucket, detail), ("blocked", "captcha redirect"))


class TestClassifyOffsiteCareers(unittest.TestCase):
    def test_offsite_careers_link(self) -> None:
        probe = make_probe(
            status=200,
            html="<html><body><a href='https://acme.peopleforce.io/careers'>Careers</a></body></html>",
            links=["https://acme.peopleforce.io/careers"],
        )
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "offsite_careers")
        self.assertIn("peopleforce", detail)

    def test_same_host_link_does_not_count_as_offsite(self) -> None:
        probe = make_probe(
            status=200,
            html="<html><body>Careers at Acme</body></html>",
            links=["https://acme.example.com/careers/open-positions"],
        )
        bucket, _detail = classify(probe)
        self.assertNotEqual(bucket, "offsite_careers")

    def test_noise_host_does_not_count_as_offsite(self) -> None:
        probe = make_probe(
            status=200,
            html="<html><body>Careers at Acme</body></html>",
            links=["https://www.linkedin.com/jobs/acme"],
        )
        bucket, _detail = classify(probe)
        self.assertNotEqual(bucket, "offsite_careers")

    def test_ats_discoverable_wins_over_offsite_careers_link(self) -> None:
        html = """
        <html><body>
        <iframe src="https://boards.greenhouse.io/acme"></iframe>
        </body></html>
        """
        probe = make_probe(
            status=200,
            html=html,
            links=["https://acme.peopleforce.io/careers"],
        )
        bucket, detail = classify(probe)
        self.assertEqual((bucket, detail), ("ats_discoverable", "greenhouse"))


class TestClassifyStorefront(unittest.TestCase):
    SHOPIFY_HTML = """
    <html><body>
    <h1>Careers at Acme</h1>
    <script src="https://cdn.shopify.com/s/files/theme.js"></script>
    </body></html>
    """

    def test_shopify_page_with_no_job_links_is_storefront(self) -> None:
        probe = make_probe(status=200, html=self.SHOPIFY_HTML, job_link_count=0)
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "storefront")
        self.assertEqual(detail, "cdn.shopify.com")

    def test_shopify_page_with_job_links_falls_to_extractor_gap(self) -> None:
        probe = make_probe(status=200, html=self.SHOPIFY_HTML, job_link_count=3)
        bucket, _detail = classify(probe)
        self.assertEqual(bucket, "extractor_gap")


class TestClassifyCareersLanding(unittest.TestCase):
    def test_same_host_deeper_link_is_careers_landing(self) -> None:
        probe = PageProbe(
            company_id=1,
            company_name="Acme",
            url="https://acme.com/careers",
            status=200,
            html="<html><body><h1>Careers</h1></body></html>",
            links=["https://acme.com/careers/open-positions"],
            job_link_count=0,
        )
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "careers_landing")
        self.assertIn("open-positions", detail)

    def test_link_that_is_just_the_page_url_is_not_careers_landing(self) -> None:
        probe = PageProbe(
            company_id=1,
            company_name="Acme",
            url="https://acme.com/careers",
            status=200,
            html="<html><body><h1>Careers</h1></body></html>",
            links=["https://acme.com/careers/"],
            job_link_count=0,
        )
        bucket, _detail = classify(probe)
        self.assertNotEqual(bucket, "careers_landing")
        self.assertEqual(bucket, "unknown")


class TestClassifyUnknown(unittest.TestCase):
    def test_empty_ish_page_with_careers_vocabulary(self) -> None:
        html = "<html><body><h1>Careers at Acme</h1></body></html>"
        probe = make_probe(status=200, html=html, job_link_count=0)
        bucket, detail = classify(probe)
        self.assertEqual(bucket, "unknown")
        self.assertEqual(detail, "")


class TestClassifyPerformance(unittest.TestCase):
    def test_large_repeated_char_page_classifies_quickly(self) -> None:
        html = "z" * 50000
        probe = make_probe(status=200, html=html, job_link_count=0)
        start = time.monotonic()
        classify(probe)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 1.0)


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


class TestProbeFromDict(unittest.TestCase):
    def test_round_trip(self) -> None:
        probe = make_probe(
            status=200,
            error=None,
            html="<html><body>Careers</body></html>",
            final_url="https://acme.example.com/careers/",
            links=["https://acme.example.com/careers/1"],
            json_endpoints=["https://acme.example.com/api/jobs"],
            job_link_count=3,
        )
        rebuilt = probe_from_dict(asdict(probe))
        self.assertEqual(rebuilt, probe)


if __name__ == "__main__":
    unittest.main()
