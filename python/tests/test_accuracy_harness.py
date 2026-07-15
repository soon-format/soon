"""Plumbing test for the retrieval-accuracy harness.

Runs the CLI end-to-end against the mock provider on a tiny slice and
asserts a clean 100% score + well-formed report. Catches regressions
in question generators, formatters, provider protocol, scoring, and
report aggregation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolate_results(monkeypatch, tmp_path):
    """Redirect the harness's results dir to a tmp path so the test never
    leaves artifacts and can't collide with a real local run."""
    from benchmarks.accuracy import report, storage

    models_dir = tmp_path / "models"
    monkeypatch.setattr(storage, "_RESULTS_ROOT", models_dir)
    monkeypatch.setattr(report, "_REPORT_PATH", tmp_path / "retrieval-accuracy.md")
    return tmp_path


def test_mock_harness_end_to_end(_isolate_results):
    from benchmarks.accuracy import run

    rc = run.main(
        [
            "--provider", "mock:fixture",
            "--dry-run",
            "--format", "json",
            "--format", "soon",
        ]
    )
    assert rc == 0

    model_file = _isolate_results / "models" / "mock_fixture.json"
    assert model_file.exists()
    payload = json.loads(model_file.read_text())
    assert payload["model"] == "mock:fixture"
    assert len(payload["results"]) == 20  # 10 questions x 2 formats
    assert all(r["correct"] for r in payload["results"])

    report_file = _isolate_results / "retrieval-accuracy.md"
    assert report_file.exists()
    report_text = report_file.read_text()
    assert "Overall accuracy" in report_text
    assert "mock:fixture" in report_text


def test_question_generators_are_deterministic():
    from benchmarks.accuracy.questions import all_questions
    from benchmarks.datasets import (
        l2_flat_table,
        l5_nested_uniform_large,
        l6_deeply_nested,
        l7_semi_uniform,
        l10_sparse_api_response,
        l11_shared_address_employees,
    )

    ds1 = {
        "L2": l2_flat_table(),
        "L5": l5_nested_uniform_large(),
        "L6": l6_deeply_nested(),
        "L7": l7_semi_uniform(),
        "L10": l10_sparse_api_response(),
        "L11": l11_shared_address_employees(),
    }
    ds2 = {k: fn() for k, fn in [
        ("L2", l2_flat_table), ("L5", l5_nested_uniform_large),
        ("L6", l6_deeply_nested), ("L7", l7_semi_uniform),
        ("L10", l10_sparse_api_response), ("L11", l11_shared_address_employees),
    ]}
    q1 = all_questions(ds1)
    q2 = all_questions(ds2)
    assert len(q1) == len(q2)
    assert len(q1) >= 200, f"expected ≥200 questions, got {len(q1)}"
    for a, b in zip(q1, q2, strict=True):
        assert a == b


def test_all_formats_render_all_datasets():
    """Cheap smoke check: every (dataset, format) combo produces a string."""
    from benchmarks.accuracy.formats import PRIMERS, render
    from benchmarks.accuracy.run import DATASETS

    for ds_name, data in DATASETS.items():
        for fmt in PRIMERS:
            if fmt == "toon":
                continue  # optional dep
            rendered = render(data, fmt)
            assert isinstance(rendered, str) and rendered, f"{ds_name}/{fmt} empty"
