"""The eval metrics themselves (pure functions, no LLM)."""

import pytest
from evals.metrics import count_lines, extraction_counts, fit_bucket, precision_recall

from tests.fakes import good_cv, good_letter


def test_extraction_counts_fuzzy_matches_both_ways():
    gold = ["Python", "SQL", "Experience with REST APIs"]
    got = ["Python programming", "REST APIs", "Docker"]

    assert extraction_counts(gold, got) == (2, 1, 1)  # tp, fp, fn


def test_extraction_counts_empty_prediction():
    assert extraction_counts(["Python"], []) == (0, 0, 1)


def test_precision_recall_handles_zero_division():
    assert precision_recall(0, 0, 0) == (0.0, 0.0)
    assert precision_recall(3, 1, 2) == (0.75, 0.6)


@pytest.mark.parametrize(
    ("score", "bucket"), [(0, "low"), (49.9, "low"), (50, "medium"), (74.9, "medium"), (75, "high")]
)
def test_fit_bucket_boundaries(score, bucket):
    assert fit_bucket(score) == bucket


def test_count_lines_counts_every_generated_sentence():
    # summary + 2 bullets + 2 letter paragraphs
    assert count_lines(good_cv(), good_letter()) == 5
    assert count_lines(good_cv(), None) == 3


def test_runner_end_to_end_with_scripted_llm(fake_llm):
    from evals import run_evals

    from tests.fakes import happy_script

    fake_llm(happy_script())
    cases = [c for c in run_evals.load_cases(None) if c["id"] in ("p01", "p08")]

    report = run_evals.evaluate("fake-model", cases, full=True)
    md = run_evals.to_markdown([report], cases, full=True)

    assert report.errors == []
    assert report.fit_pairs == [("p01", "high", "high")]  # scripted fit is 80.0
    assert report.vague_correct == 1  # p01 correct, p08 (scripted not vague) wrong
    assert report.first_pass_ok == 1
    assert "| fake-model |" in md
