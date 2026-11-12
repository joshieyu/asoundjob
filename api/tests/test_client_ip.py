from __future__ import annotations

import unittest

from api.rate_limit import client_ip, parse_networks

PROXIES = parse_networks(["127.0.0.1", "::1", "172.18.0.0/16"])


class FakeClient:
    def __init__(self, host: str) -> None:
        self.host = host


class FakeRequest:
    def __init__(self, host: str, headers: dict) -> None:
        self.client = FakeClient(host)
        self.headers = headers


class TestClientIp(unittest.TestCase):
    def test_direct_client_ignores_forwarded_headers(self) -> None:
        request = FakeRequest("198.51.100.4", {"x-forwarded-for": "1.2.3.4"})
        self.assertEqual(client_ip(request, PROXIES), "198.51.100.4")

    def test_trusted_proxy_uses_forwarded_client(self) -> None:
        request = FakeRequest("127.0.0.1", {"x-forwarded-for": "203.0.113.20"})
        self.assertEqual(client_ip(request, PROXIES), "203.0.113.20")

    def test_spoofed_leftmost_hop_is_ignored(self) -> None:
        request = FakeRequest(
            "172.18.0.5", {"x-forwarded-for": "6.6.6.6, 203.0.113.20, 172.18.0.2"}
        )
        self.assertEqual(client_ip(request, PROXIES), "203.0.113.20")

    def test_trusted_proxy_without_header_falls_back(self) -> None:
        self.assertEqual(
            client_ip(FakeRequest("127.0.0.1", {"x-real-ip": "203.0.113.30"}), PROXIES),
            "203.0.113.30",
        )
        self.assertEqual(client_ip(FakeRequest("::1", {}), PROXIES), "::1")

    def test_request_without_client_or_headers(self) -> None:
        class Bare:
            client = None

        self.assertEqual(client_ip(Bare(), PROXIES), "unknown")

    def test_invalid_entries_are_skipped(self) -> None:
        self.assertEqual(len(parse_networks(["10.0.0.0/8", "nonsense", ""])), 1)


if __name__ == "__main__":
    unittest.main()
