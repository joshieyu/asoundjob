from __future__ import annotations

import unittest

from scraper.audit_seed_urls import classify, render


class TestClassify(unittest.TestCase):
    def test_bucket_d_error_page(self) -> None:
        rows = [
            {
                "name": "Broken Co",
                "careers_url": "https://broken.example/careers/404",
                "verified": True,
            }
        ]
        result = classify(rows)
        self.assertEqual(len(result.bad_page), 1)
        self.assertEqual(result.bad_page[0].company, "Broken Co")
        self.assertEqual(len(result.wrong_host_no_vocab), 0)
        self.assertEqual(len(result.right_host_no_vocab), 0)
        self.assertEqual(len(result.wrong_host_careers_shaped), 0)

    def test_bucket_a_wrong_host_no_vocab(self) -> None:
        rows = [
            {
                "name": "Widgetco",
                "careers_url": "https://totallyunrelated.example/about",
                "verified": False,
            }
        ]
        result = classify(rows)
        self.assertEqual(len(result.wrong_host_no_vocab), 1)
        self.assertEqual(result.wrong_host_no_vocab[0].company, "Widgetco")
        self.assertEqual(len(result.bad_page), 0)
        self.assertEqual(len(result.right_host_no_vocab), 0)
        self.assertEqual(len(result.wrong_host_careers_shaped), 0)

    def test_bucket_c_right_host_no_vocab(self) -> None:
        rows = [
            {
                "name": "Widgetco",
                "careers_url": "https://widgetco.com/about-us",
                "verified": True,
            }
        ]
        result = classify(rows)
        self.assertEqual(len(result.right_host_no_vocab), 1)
        self.assertEqual(result.right_host_no_vocab[0].company, "Widgetco")
        self.assertEqual(len(result.bad_page), 0)
        self.assertEqual(len(result.wrong_host_no_vocab), 0)
        self.assertEqual(len(result.wrong_host_careers_shaped), 0)

    def test_bucket_b_wrong_host_careers_shaped_is_counted_not_a_bug(self) -> None:
        rows = [
            {
                "name": "Soundtrap",
                "careers_url": "https://www.lifeatspotify.com/jobs",
                "verified": True,
            }
        ]
        result = classify(rows)
        self.assertEqual(len(result.wrong_host_careers_shaped), 1)
        self.assertEqual(result.wrong_host_careers_shaped[0].company, "Soundtrap")
        self.assertEqual(len(result.bad_page), 0)
        self.assertEqual(len(result.wrong_host_no_vocab), 0)
        self.assertEqual(len(result.right_host_no_vocab), 0)

    def test_ats_hosted_url_is_skipped_entirely(self) -> None:
        rows = [
            {
                "name": "Anything",
                "careers_url": "https://boards.greenhouse.io/anything",
                "verified": True,
            }
        ]
        result = classify(rows)
        self.assertEqual(len(result.bad_page), 0)
        self.assertEqual(len(result.wrong_host_no_vocab), 0)
        self.assertEqual(len(result.right_host_no_vocab), 0)
        self.assertEqual(len(result.wrong_host_careers_shaped), 0)

    def test_shopify_style_pages_careers_is_not_flagged(self) -> None:
        rows = [
            {
                "name": "Widgetco",
                "careers_url": "https://widgetco.com/pages/careers",
                "verified": True,
            }
        ]
        result = classify(rows)
        self.assertEqual(len(result.bad_page), 0)
        self.assertEqual(len(result.wrong_host_no_vocab), 0)
        self.assertEqual(len(result.right_host_no_vocab), 0)
        self.assertEqual(len(result.wrong_host_careers_shaped), 0)

    def test_name_token_in_host_does_not_land_in_bucket_a(self) -> None:
        rows = [
            {
                "name": "Widgetco",
                "careers_url": "https://widgetco.com/about-us",
                "verified": False,
            }
        ]
        result = classify(rows)
        self.assertEqual(len(result.wrong_host_no_vocab), 0)
        self.assertEqual(len(result.right_host_no_vocab), 1)

    def test_url_with_no_scheme_or_host_is_skipped(self) -> None:
        rows = [
            {
                "name": "Nowhere",
                "careers_url": "not-a-url-at-all",
                "verified": True,
            }
        ]
        result = classify(rows)
        self.assertEqual(len(result.bad_page), 0)
        self.assertEqual(len(result.wrong_host_no_vocab), 0)
        self.assertEqual(len(result.right_host_no_vocab), 0)
        self.assertEqual(len(result.wrong_host_careers_shaped), 0)

    def test_missing_careers_url_is_skipped(self) -> None:
        rows = [{"name": "Empty", "careers_url": "", "verified": False}]
        result = classify(rows)
        self.assertEqual(len(result.bad_page), 0)
        self.assertEqual(len(result.wrong_host_no_vocab), 0)
        self.assertEqual(len(result.right_host_no_vocab), 0)
        self.assertEqual(len(result.wrong_host_careers_shaped), 0)


class TestRender(unittest.TestCase):
    def test_render_states_it_is_read_only_and_needs_confirmation(self) -> None:
        rows: list[dict] = []
        out = render(classify(rows))
        self.assertIn("Read-only", out)
        self.assertIn("proposal list requiring human confirmation", out)
        self.assertIn("lifeatspotify.com", out)

    def test_render_output_contains_the_counts(self) -> None:
        rows = [
            {
                "name": "Broken Co",
                "careers_url": "https://broken.example/careers/404",
                "verified": True,
            },
            {
                "name": "Widgetco",
                "careers_url": "https://totallyunrelated.example/about",
                "verified": False,
            },
            {
                "name": "Otherco",
                "careers_url": "https://otherco.com/about-us",
                "verified": True,
            },
            {
                "name": "Soundtrap",
                "careers_url": "https://www.lifeatspotify.com/jobs",
                "verified": True,
            },
        ]
        result = classify(rows)
        out = render(result)
        self.assertIn("entries flagged: 3", out)
        self.assertIn(f"D — error / for-sale / press release: {len(result.bad_page)}", out)
        self.assertIn(
            f"A — wrong host, no careers vocabulary: {len(result.wrong_host_no_vocab)}", out
        )
        self.assertIn(
            f"C — right host, no careers vocabulary: {len(result.right_host_no_vocab)}", out
        )
        self.assertIn(
            "B — wrong host, careers-shaped (likely parent company, not listed): "
            f"{len(result.wrong_host_careers_shaped)}",
            out,
        )
        self.assertIn("Broken Co", out)
        self.assertIn("Widgetco", out)
        self.assertIn("Otherco", out)
        self.assertNotIn("https://www.lifeatspotify.com/jobs", out)


if __name__ == "__main__":
    unittest.main()
