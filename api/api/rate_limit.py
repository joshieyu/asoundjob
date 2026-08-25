from __future__ import annotations

import time
from collections import defaultdict


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
