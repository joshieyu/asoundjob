import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch


class MaskProxyTests(unittest.TestCase):
    def test_strips_scheme_and_credentials(self) -> None:
        cases = [
            "user:pass@host.example.com:8080",
            "http://user:pass@host.example.com:8080",
            "https://user:pass@host.example.com:8080",
            "socks5://user:pass@host.example.com:8080",
        ]
        for proxy in cases:
            with self.subTest(proxy=proxy):
                self.assertEqual(fetch.mask_proxy(proxy), "host.example.com:8080")

    def test_bare_host_port_unchanged(self) -> None:
        self.assertEqual(fetch.mask_proxy("host.example.com:8080"), "host.example.com:8080")

    def test_never_leaks_credentials(self) -> None:
        masked = fetch.mask_proxy("http://sneaky_user:sneaky_pass@host.example.com:8080")
        self.assertNotIn("sneaky_user", masked)
        self.assertNotIn("sneaky_pass", masked)


class ProxiesFileTests(unittest.TestCase):
    def test_parses_comments_and_blanks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proxies.txt"
            path.write_text(
                "\n".join(
                    [
                        "# a comment",
                        "",
                        "user:pass@a.example.com:8080",
                        "   ",
                        "# another comment",
                        "user:pass@b.example.com:8081",
                    ]
                ),
                encoding="utf-8",
            )
            proxies = fetch.read_proxies_file(path)
        self.assertEqual(
            proxies,
            ["user:pass@a.example.com:8080", "user:pass@b.example.com:8081"],
        )


class ResolveProxiesTests(unittest.TestCase):
    def test_env_var_used_when_no_file(self) -> None:
        with mock.patch.dict(
            "os.environ", {"JOBSPY_PROXIES": "a.example.com:1,b.example.com:2"}, clear=False
        ):
            proxies = fetch.resolve_proxies(None)
        self.assertEqual(proxies, ["a.example.com:1", "b.example.com:2"])

    def test_file_wins_over_env_var(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proxies.txt"
            path.write_text("file.example.com:9\n", encoding="utf-8")
            with mock.patch.dict(
                "os.environ", {"JOBSPY_PROXIES": "env.example.com:1"}, clear=False
            ):
                proxies = fetch.resolve_proxies(path)
        self.assertEqual(proxies, ["file.example.com:9"])

    def test_no_file_no_env_returns_empty(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(fetch.resolve_proxies(None), [])

    def test_file_with_zero_entries_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proxies.txt"
            path.write_text("# only comments\n\n", encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                fetch.resolve_proxies(path)
        self.assertNotEqual(ctx.exception.code, 0)


class LinkedinGuardTests(unittest.TestCase):
    def _argv(self, extra: list[str], output: Path) -> list[str]:
        return [
            "fetch.py",
            "--sites",
            "linkedin",
            "--output",
            str(output),
            *extra,
        ]

    def test_zero_proxies_exits_without_calling_scrape_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.json"
            with mock.patch.object(fetch, "scrape_jobs") as scrape_mock, mock.patch.dict(
                "os.environ", {}, clear=True
            ), mock.patch("sys.argv", self._argv([], output)):
                with self.assertRaises(SystemExit) as ctx:
                    fetch.main()
            self.assertNotEqual(ctx.exception.code, 0)
            scrape_mock.assert_not_called()

    def test_escape_hatch_permits_unprotected_run(self) -> None:
        try:
            fetch.require_proxy_for_linkedin(["linkedin"], [], allow_unprotected=True)
        except SystemExit:
            self.fail("escape hatch flag should not exit")

    def test_no_proxy_no_escape_hatch_exits(self) -> None:
        with self.assertRaises(SystemExit):
            fetch.require_proxy_for_linkedin(["linkedin"], [], allow_unprotected=False)

    def test_indeed_only_does_not_require_proxy(self) -> None:
        try:
            fetch.require_proxy_for_linkedin(["indeed"], [], allow_unprotected=False)
        except SystemExit:
            self.fail("indeed-only sites should not require a proxy")


class PreflightProxiesTests(unittest.TestCase):
    def test_rejects_proxy_matching_direct_ip(self) -> None:
        def fake_fetch_ip(proxies, timeout):
            return "1.2.3.4"

        usable = fetch.preflight_proxies(
            ["user:pass@a.example.com:8080"], fetch_ip=fake_fetch_ip
        )
        self.assertEqual(usable, [])

    def test_accepts_proxy_with_different_ip(self) -> None:
        def fake_fetch_ip(proxies, timeout):
            if proxies is None:
                return "1.2.3.4"
            return "9.9.9.9"

        usable = fetch.preflight_proxies(
            ["user:pass@a.example.com:8080"], fetch_ip=fake_fetch_ip
        )
        self.assertEqual(usable, ["user:pass@a.example.com:8080"])

    def test_allow_partial_semantics_keeps_only_passing(self) -> None:
        direct_ip = "1.2.3.4"

        def fake_fetch_ip(proxies, timeout):
            if proxies is None:
                return direct_ip
            if proxies["http"] == "http://good.example.com:1":
                return "5.5.5.5"
            return direct_ip

        proxies = ["good.example.com:1", "bad.example.com:2"]
        usable = fetch.preflight_proxies(proxies, fetch_ip=fake_fetch_ip)
        self.assertEqual(usable, ["good.example.com:1"])
        self.assertLess(len(usable), len(proxies))

    def test_proxy_raising_is_treated_as_failure(self) -> None:
        def fake_fetch_ip(proxies, timeout):
            if proxies is None:
                return "1.2.3.4"
            raise OSError("connection refused")

        usable = fetch.preflight_proxies(["dead.example.com:1"], fetch_ip=fake_fetch_ip)
        self.assertEqual(usable, [])


class BlockDetectorTests(unittest.TestCase):
    def _make_record(self, message: str) -> logging.LogRecord:
        return logging.LogRecord(
            name=fetch.LINKEDIN_LOGGER_NAME,
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )

    def test_trips_on_429_message(self) -> None:
        detector = fetch.LinkedInBlockDetector()
        detector.emit(self._make_record(fetch.BLOCK_MESSAGE_429))
        self.assertTrue(detector.blocked)
        self.assertEqual(detector.reason, fetch.BLOCK_MESSAGE_429)

    def test_trips_on_bad_proxy(self) -> None:
        detector = fetch.LinkedInBlockDetector()
        detector.emit(self._make_record("LinkedIn: Bad proxy"))
        self.assertTrue(detector.blocked)
        self.assertEqual(detector.reason, fetch.BLOCK_MESSAGE_BAD_PROXY)

    def test_unrelated_message_does_not_trip(self) -> None:
        detector = fetch.LinkedInBlockDetector()
        detector.emit(self._make_record("LinkedIn: something unrelated happened"))
        self.assertFalse(detector.blocked)


class OutputPayloadTests(unittest.TestCase):
    def test_no_proxy_credentials_in_output(self) -> None:
        proxy = "supersecretuser:supersecretpass@proxy.example.com:8080"
        fake_df = mock.Mock()
        fake_df.empty = True

        with tempfile.TemporaryDirectory() as tmp:
            terms_file = Path(tmp) / "terms.txt"
            terms_file.write_text("audio engineer\n", encoding="utf-8")
            output = Path(tmp) / "out.json"

            with mock.patch.object(fetch, "scrape_jobs", return_value=fake_df) as scrape_mock:
                fetch.run(
                    terms_file,
                    ["indeed"],
                    5,
                    720,
                    "",
                    "usa",
                    output,
                    [proxy],
                    False,
                    0.0,
                    None,
                )

            raw_text = output.read_text(encoding="utf-8")
            self.assertNotIn("supersecretuser", raw_text)
            self.assertNotIn("supersecretpass", raw_text)

            payload = json.loads(raw_text)
            self.assertEqual(payload["proxy_count"], 1)
            self.assertNotIn("proxies", payload)

            called_kwargs = scrape_mock.call_args.kwargs
            self.assertEqual(called_kwargs["proxies"], [proxy])


if __name__ == "__main__":
    unittest.main()
