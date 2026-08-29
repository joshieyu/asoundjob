from __future__ import annotations

import time
import unittest

from scraper.scrapers.ats_discovery import discover, first_discovery

GREENHOUSE_IFRAME = """
<html><body>
<iframe src="https://boards.greenhouse.io/embed/job_board?for=acme"></iframe>
</body></html>
"""

LEVER_LINK = """
<html><body>
<a href="https://jobs.lever.co/acme-inc">View Open Roles</a>
</body></html>
"""

WORKABLE_SCRIPT = """
<html><body>
<script src="https://apply.workable.com/acme-widget.js"></script>
</body></html>
"""

WORKDAY_LINK = """
<html><body>
<a href="https://acme.wd1.myworkdayjobs.com/Acme_Careers">Careers</a>
</body></html>
"""

MULTIPLE_ATS = """
<html><body>
<a href="https://jobs.lever.co/acme">Jobs</a>
<script src="https://boards.greenhouse.io/embed/job_board?for=acme"></script>
</body></html>
"""

NO_ATS = """
<html><body>
<h1>Work at Acme</h1>
<p>Email us at careers@acme.com</p>
</body></html>
"""

APPLE_PAGE = """
<html><body>
<a href="https://jobs.apple.com/en-us/search">View Jobs</a>
</body></html>
"""


class TestATSDiscovery(unittest.TestCase):
    def test_greenhouse_iframe(self) -> None:
        results = discover(GREENHOUSE_IFRAME)
        self.assertEqual(results[0], ("greenhouse", "acme"))

    def test_lever_link(self) -> None:
        results = discover(LEVER_LINK)
        self.assertEqual(results[0], ("lever", "acme-inc"))

    def test_workable_script(self) -> None:
        results = discover(WORKABLE_SCRIPT)
        self.assertEqual(results[0], ("workable", "acme-widget"))

    def test_workday_link(self) -> None:
        results = discover(WORKDAY_LINK)
        self.assertEqual(results[0], ("workday", "Acme_Careers"))

    def test_multiple_ats(self) -> None:
        results = discover(MULTIPLE_ATS)
        types = [r[0] for r in results]
        self.assertIn("lever", types)
        self.assertIn("greenhouse", types)

    def test_no_ats(self) -> None:
        results = discover(NO_ATS)
        self.assertEqual(len(results), 0)

    def test_apple(self) -> None:
        results = discover(APPLE_PAGE)
        self.assertEqual(results[0], ("apple", ""))

    def test_first_discovery(self) -> None:
        result = first_discovery(GREENHOUSE_IFRAME)
        self.assertEqual(result, ("greenhouse", "acme"))

    def test_first_discovery_none(self) -> None:
        self.assertIsNone(first_discovery(NO_ATS))

    def test_long_word_run_is_not_quadratic(self) -> None:
        page = '<img src="data:image/png;base64,' + "iVBORw0KGgoAAAANSUhEUgAA" * 2000 + '">'
        started = time.monotonic()
        self.assertEqual(discover(page), [])
        self.assertLess(time.monotonic() - started, 2.0)

    def test_dedupe(self) -> None:
        html = '<a href="https://jobs.lever.co/acme">1</a><a href="https://jobs.lever.co/acme/123">2</a>'
        results = discover(html)
        lever_results = [r for r in results if r[0] == "lever"]
        self.assertEqual(len(lever_results), 1)


if __name__ == "__main__":
    unittest.main()
