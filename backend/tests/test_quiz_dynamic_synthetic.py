"""Synthetic fixture provenance, reproducibility and feature-contract checks."""

from collections import Counter

import pytest

from app.modules.quiz.dynamic_ml_features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from scripts.generate_quiz_dynamic_synthetic import (
    DATA_ORIGIN, TARGET_NAMES, build_dataset,
)


def test_synthetic_rows_use_real_bank_and_exact_extractor_schema():
    rows, report = build_dataset(96, seed=20261022)
    assert len(rows) == 96
    assert len(report["coverage"]) == 60
    assert set(report["coverage"].values()) == {16}
    assert len(report["profiles"]) == 16
    assert set(report["profiles"].values()) == {6}
    assert len({row["learner_id"] for row in rows}) == 96
    assert Counter(sum(row[target] for target in TARGET_NAMES) for row in rows) == {
        0: 6, 1: 24, 2: 36, 3: 24, 4: 6,
    }
    for row in rows:
        assert tuple(row) == FEATURE_NAMES + TARGET_NAMES + (
            "learner_id", "data_origin", "bank_version", "feature_schema_version")
        assert row["data_origin"] == DATA_ORIGIN
        assert row["feature_schema_version"] == FEATURE_SCHEMA_VERSION
        assert row["bank_version"] == "pp1_dynamic_v1_DRAFT"
        assert all(row[target] in (0, 1) for target in TARGET_NAMES)
        assert row["correct_count"] + row["incorrect_count"] == 10
        assert row["easy_correct_count"] <= 4
        assert row["medium_correct_count"] <= 4
        assert row["hard_correct_count"] <= 2
        assert row["response_time_min_sec"] >= 2
        assert row["response_time_max_sec"] <= 100
        assert sum(row[f"confidence_{level}_count"] for level in
                   ("low", "medium", "high")) == 10
        assert sum(row[f"option_{tag}_count"] for tag in
                   ("inverse_operation", "sign_error", "arithmetic_error",
                    "concept_confusion")) == row["incorrect_count"]


def test_same_seed_produces_identical_rows():
    assert build_dataset(96, seed=17)[0] == build_dataset(96, seed=17)[0]


def test_invalid_row_count_rejected():
    with pytest.raises(ValueError, match="divisible by 16"):
        build_dataset(97)
