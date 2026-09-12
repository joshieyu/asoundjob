from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "asj-edited.svg"

LIGHT_GROUND = "#0033ff"
LIGHT_MARK = "#f9f9f8"
DARK_GROUND = "#5c7bff"
DARK_MARK = "#131314"

NUMBER_RE = re.compile(r"-?\d+\.?\d*")
PATH_RE = re.compile(r'\bd="([^"]{1,20000})"')


def a_path() -> str:
    return PATH_RE.findall(SOURCE.read_text())[0]


def points(d: str) -> List[Tuple[float, float]]:
    nums = [float(n) for n in NUMBER_RE.findall(d)]
    return list(zip(nums[0::2], nums[1::2]))


def bounds(pts: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    xs: List[float] = [pts[0][0]]
    ys: List[float] = [pts[0][1]]
    cur = pts[0]
    rest = pts[1:]
    for i in range(0, len(rest), 3):
        p1, p2, p3 = rest[i], rest[i + 1], rest[i + 2]
        for k in range(41):
            t = k / 40
            u = 1 - t
            xs.append(u**3 * cur[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0])
            ys.append(u**3 * cur[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1])
        cur = p3
    return min(xs), min(ys), max(xs), max(ys)


def fit(size: float, glyph_fraction: float, stroke_fraction: float) -> Tuple[str, float]:
    pts = points(a_path())
    x0, y0, x1, y1 = bounds(pts)
    stroke = size * stroke_fraction
    scale = (size * glyph_fraction) / (y1 - y0)
    tx = (size - (x1 - x0) * scale) / 2 - x0 * scale
    ty = (size - (y1 - y0) * scale) / 2 - y0 * scale
    moved = [(x * scale + tx, y * scale + ty) for x, y in pts]
    d = f"M{moved[0][0]:.3f} {moved[0][1]:.3f}"
    for i in range(1, len(moved), 3):
        a, b, c = moved[i], moved[i + 1], moved[i + 2]
        d += (
            f"C{a[0]:.3f} {a[1]:.3f} {b[0]:.3f} {b[1]:.3f} {c[0]:.3f} {c[1]:.3f}"
        )
    return d, stroke


def svg(size: float, d: str, stroke: float, themed: bool) -> str:
    style = (
        f"<style>:root{{--g:{LIGHT_GROUND};--m:{LIGHT_MARK}}}"
        f"@media (prefers-color-scheme:dark){{:root{{--g:{DARK_GROUND};--m:{DARK_MARK}}}}}</style>"
    )
    ground = "var(--g)" if themed else LIGHT_GROUND
    mark = "var(--m)" if themed else LIGHT_MARK
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size:g} {size:g}">'
        f"{style if themed else ''}"
        f'<rect width="{size:g}" height="{size:g}" fill="{ground}"/>'
        f'<path d="{d}" fill="none" stroke="{mark}" stroke-width="{stroke:.3f}"'
        f' stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def main() -> None:
    d32, s32 = fit(32, 0.6875, 0.10625)
    d180, s180 = fit(180, 0.66, 0.09)
    (HERE / "favicon-asj.svg").write_text(svg(32, d32, s32, True) + "\n")
    (HERE / "favicon-asj-flat.svg").write_text(svg(32, d32, s32, False) + "\n")
    (HERE / "favicon-asj-180.svg").write_text(svg(180, d180, s180, False) + "\n")


if __name__ == "__main__":
    main()
