from __future__ import annotations

import sys
from pathlib import Path

_SCRAPER_DIR = str(Path(__file__).resolve().parents[2] / "scraper")
if _SCRAPER_DIR not in sys.path:
    sys.path.insert(0, _SCRAPER_DIR)
