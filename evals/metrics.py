"""Pure metric functions for the eval runner (unit-tested in backend/tests)."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Literal

from app.schemas import CoverLetter, TailoredCV

FitBucket = Literal["low", "medium", "high"]


def similar(a: str, b: str) -> bool:
    """Loose requirement match: containment either way, or high character overlap."""
    a, b = a.lower().strip(), b.lower().strip()
    return a in b or b in a or SequenceMatcher(None, a, b).ratio() > 0.6


def extraction_counts(gold: list[str], got: list[str]) -> tuple[int, int, int]:
    """(true positives, false positives, false negatives) of extracted vs gold requirements."""
    tp = sum(1 for g in gold if any(similar(g, p) for p in got))
    fp = sum(1 for p in got if not any(similar(g, p) for g in gold))
    return tp, fp, len(gold) - tp


def precision_recall(tp: int, fp: int, fn: int) -> tuple[float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return round(precision, 2), round(recall, 2)


def fit_bucket(score: float) -> FitBucket:
    if score < 50:
        return "low"
    return "medium" if score < 75 else "high"


def count_lines(cv: TailoredCV, letter: CoverLetter | None) -> int:
    """Generated sentences that carry evidence: summary, bullets, letter paragraphs."""
    bullets = sum(len(e.bullets) for e in cv.entries)
    return 1 + bullets + (len(letter.paragraphs) if letter else 0)
