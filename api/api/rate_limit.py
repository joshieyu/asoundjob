from __future__ import annotations

import ipaddress
import time
from collections import defaultdict
from typing import Any, Optional, Sequence, Union

from api.config import TRUSTED_PROXIES

IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


def parse_networks(values: Sequence[str]) -> list[IPNetwork]:
    networks: list[IPNetwork] = []
    for value in values:
        try:
            networks.append(ipaddress.ip_network(value.strip(), strict=False))
        except ValueError:
            continue
    return networks


def _is_trusted(address: str, networks: Sequence[IPNetwork]) -> bool:
    try:
        ip = ipaddress.ip_address(address.strip())
    except ValueError:
        return False
    return any(ip in network for network in networks)


def client_ip(request: Any, trusted: Optional[Sequence[IPNetwork]] = None) -> str:
    networks = TRUSTED_NETWORKS if trusted is None else trusted
    client = getattr(request, "client", None)
    peer = getattr(client, "host", None) or "unknown"
    if not _is_trusted(peer, networks):
        return peer
    headers = getattr(request, "headers", None) or {}
    forwarded = headers.get("x-forwarded-for", "")
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    for hop in reversed(hops):
        if not _is_trusted(hop, networks):
            return hop
    real_ip = headers.get("x-real-ip", "").strip()
    return real_ip or peer


TRUSTED_NETWORKS = parse_networks(TRUSTED_PROXIES)


class SubmissionRateLimiter:
    def __init__(self, max_per_day: int = 3, window_seconds: int = 86400) -> None:
        self.max_per_day = max_per_day
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> tuple[bool, str]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        hits = [ts for ts in self._hits.get(key, []) if ts > cutoff]
        if len(hits) >= self.max_per_day:
            retry_after = int(hits[0] + self.window_seconds - now)
            minutes = max(1, retry_after // 60)
            return False, f"retry in ~{minutes} min"
        hits.append(now)
        self._hits[key] = hits
        return True, ""

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._hits.clear()
        else:
            self._hits.pop(key, None)
