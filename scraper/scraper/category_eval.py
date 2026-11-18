from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scraper.normalizer import classify_categories

GOLDEN_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "category_golden.json"


@dataclass
class EvalResult:
    total: int = 0
    empty: int = 0
    hit: int = 0
    clean: int = 0
    wrong_labels: int = 0
    predicted_labels: int = 0
    misses: list[dict[str, Any]] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        return (self.total - self.empty) / self.total if self.total else 0.0

    @property
    def hit_rate(self) -> float:
        return self.hit / self.total if self.total else 0.0

    @property
    def clean_rate(self) -> float:
        return self.clean / self.total if self.total else 0.0

    @property
    def label_precision(self) -> float:
        if not self.predicted_labels:
            return 0.0
        return (self.predicted_labels - self.wrong_labels) / self.predicted_labels


def load_golden(path: Path = GOLDEN_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else []


def evaluate(cases: list[dict[str, Any]]) -> EvalResult:
    result = EvalResult()
    for case in cases:
        predicted = set(
            classify_categories(
                case["title"], case.get("description"), case.get("company_category")
            )
        )
        acceptable = set(case["acceptable"])
        wrong = predicted - acceptable
        result.total += 1
        result.predicted_labels += len(predicted)
        result.wrong_labels += len(wrong)
        if not predicted:
            result.empty += 1
        if predicted & acceptable:
            result.hit += 1
        if predicted and not wrong:
            result.clean += 1
        if wrong or not predicted & acceptable:
            result.misses.append(
                {
                    "id": case["id"],
                    "company": case.get("company"),
                    "title": case["title"],
                    "predicted": sorted(predicted),
                    "acceptable": sorted(acceptable),
                }
            )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Score job categorization against hand labels")
    parser.add_argument("--misses", action="store_true", help="List every job that is wrong")
    args = parser.parse_args()
    result = evaluate(load_golden())
    print(f"jobs {result.total}")
    print(f"categorized {result.coverage:.1%}")
    print(f"at least one right category {result.hit_rate:.1%}")
    print(f"all categories right {result.clean_rate:.1%}")
    print(f"label precision {result.label_precision:.1%}")
    if args.misses:
        for miss in result.misses:
            print(
                f"{miss['id']} {miss['company']} | {miss['title'][:60]} | "
                f"got {','.join(miss['predicted']) or '-'} | want {','.join(miss['acceptable'])}"
            )


if __name__ == "__main__":
    main()
