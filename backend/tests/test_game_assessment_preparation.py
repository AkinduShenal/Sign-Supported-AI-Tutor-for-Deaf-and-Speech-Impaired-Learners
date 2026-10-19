"""Invented engineering fixtures only; no genuine learner approvals or fitting."""

import copy
import csv
import hashlib
import io
import json
from datetime import date, datetime, timedelta
from zipfile import ZipFile

import pytest

from app.modules.game.ml.assessment_preparation import (
    ASSESSMENT_FIELDS,
    checked_context,
    paired_dataset,
    prepare_datasets,
    prepare,
    readiness,
    read_sheet,
    validate_assessments,
    write_csv,
)
from app.modules.game.ml.collection_research import prepare_session
from app.modules.game.ml.research_training import ExperimentConfig
from app.modules.game.ml.session_verification import FIELDS
from app.modules.game.ml.session_verification import generate_sheet
from app.modules.game.ml.teacher_assessments import (
    AFTER,
    BEFORE,
    SAME_DAY,
    TeacherAssessment,
    timing_category,
)

pytest_plugins = ["test_game_collection_research"]


def assessment(code="STU_006", score=7, level="intermediate", **changes):
    return TeacherAssessment(
        **{
            "student_code": code,
            "score": score,
            "original_score_text": str(score),
            "assessed_on": date(2026, 10, 15 if int(code[4:]) <= 7 else 16),
            "original_teacher_level": level,
            "original_source_status": "DOCUMENTED_TEACHER_LEVEL"
            if level
            else "TEACHER_SCORE_ONLY_LEVEL_NOT_PROVIDED",
            "original_suggested_level_unverified": "",
            "source_csv_sha256": "0" * 64,
            "source_row_numbers": [2],
            **changes,
        }
    )


def at(value):
    return datetime.fromisoformat(value)


@pytest.mark.parametrize(
    "start,end,expected",
    [
        ("2026-10-14T10:00:00+05:30", "2026-10-14T10:02:00+05:30", BEFORE),
        ("2026-10-15T00:00:00+05:30", "2026-10-15T00:02:00+05:30", SAME_DAY),
        ("2026-10-16T01:00:00+05:30", "2026-10-16T01:02:00+05:30", AFTER),
        ("2026-10-14T23:59:00+05:30", "2026-10-15T00:01:00+05:30", SAME_DAY),
        ("2026-10-14T19:00:00+00:00", "2026-10-14T19:02:00+00:00", SAME_DAY),
        ("2026-10-14T23:59:00+05:30", "2026-10-16T00:01:00+05:30", SAME_DAY),
    ],
)
def test_timing_uses_colombo_dates_and_whole_window(start, end, expected):
    assert timing_category(at(start), at(end), date(2026, 10, 15)) == expected


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-10-14T10:00:00", "2026-10-14T10:02:00"),
        ("2026-10-14T10:02:00+00:00", "2026-10-14T10:00:00+00:00"),
    ],
)
def test_invalid_game_times_rejected(start, end):
    with pytest.raises(ValueError):
        timing_category(at(start), at(end), date(2026, 10, 15))


@pytest.mark.parametrize(
    "score,level",
    [
        (0, "beginner"),
        (4, "beginner"),
        (5, "intermediate"),
        (7, "intermediate"),
        (8, "advanced"),
        (10, "advanced"),
    ],
)
def test_score_only_labels_are_rubric_derived(score, level):
    item = assessment(score=score, level="")
    assert item.report()["target_level"] == level
    assert item.classification_source == "TEACHER_SCORE_RUBRIC_DERIVED"
    assert item.original_source_status == "TEACHER_SCORE_ONLY_LEVEL_NOT_PROVIDED"


@pytest.mark.parametrize(
    "changes",
    [
        {"score": 11, "original_score_text": "11"},
        {"score": -1},
        {"score": True},
        {"original_score_text": "7.0"},
        {"assessed_at": "2026-10-15T12:00:00+05:30"},
        {"assessed_on": date(2026, 10, 16)},
        {"student_code": "STU_0014"},
        {"student_code": "STU_017"},
        {"original_teacher_level": ""},
        {"score_level_resolution_reference": "invented"},
    ],
)
def test_bad_assessment_evidence_rejected(changes):
    with pytest.raises(ValueError):
        assessment(**changes)


def test_score_conflict_requires_explicit_researcher_resolution():
    item = assessment("STU_008", 5, "beginner")
    assert not item.usable
    assert item.report()["target_level"] is None
    resolved = assessment(
        "STU_008",
        5,
        "beginner",
        score_level_resolution_reference="SYNTHETIC explicit researcher resolution",
    )
    assert resolved.usable
    assert resolved.original_teacher_level == "beginner"
    assert resolved.original_source_status == "DOCUMENTED_TEACHER_LEVEL"
    assert resolved.report()["target_level"] == "intermediate"
    assert resolved.classification_source == "TEACHER_SCORE_RUBRIC_DERIVED"


def input_context():
    row = dict.fromkeys(FIELDS, "")
    row.update(
        game_session_id="SYNTHETIC-review",
        student_code="STU_006",
        game_mode="drag_drop",
        answer_count="6",
        existing_verification_status="REVIEW REQUIRED",
        researcher_decision="RESEARCH_VERIFIED",
        verification_basis="SYNTHETIC researcher assertion",
    )
    return row, {"read_only_rows": [{key: row[key] for key in FIELDS[:9]}]}


def test_only_documented_status_annotation_is_restored_without_mutating_source():
    row, snapshot = input_context()
    row["existing_verification_status"] = "genuine gameplay"
    before = copy.deepcopy(row)
    compatible, restored = checked_context([row], snapshot)
    assert compatible[0]["existing_verification_status"] == "REVIEW REQUIRED"
    assert compatible[0]["researcher_decision"] == "RESEARCH_VERIFIED"
    assert len(restored) == 1
    assert row == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("student_code", "STU_007"),
        ("answer_count", "99"),
        ("started_at", "changed"),
        ("completed_at", "changed"),
        ("game_mode", "hangman"),
        ("completion_status", "completed"),
        ("teacher_label", "advanced"),
        ("existing_verification_status", "INCLUDED VERIFIED"),
    ],
)
def test_compatibility_never_hides_protected_context_changes(field, value):
    row, snapshot = input_context()
    row[field] = value
    with pytest.raises(ValueError, match="Protected"):
        checked_context([row], snapshot)


def test_missing_ids_duplicate_ids_and_extra_columns_rejected(tmp_path):
    row, snapshot = input_context()
    with pytest.raises(ValueError, match="every frozen"):
        checked_context([], snapshot)
    path = tmp_path / "SYNTHETIC-duplicate.csv"
    write_csv(path, [row, row], FIELDS)
    with pytest.raises(ValueError, match="Duplicate session"):
        read_sheet(path, FIELDS)
    path = tmp_path / "SYNTHETIC-extra.csv"
    write_csv(path, [{**row, "unapproved": "value"}])
    with pytest.raises(ValueError, match="columns"):
        read_sheet(path, FIELDS)


def assessment_sheet():
    rows, originals = [], []
    for number in range(1, 17):
        row, _ = input_context()
        row.update(
            game_session_id=f"SYNTHETIC-review-{number}",
            student_code=f"STU_{number:03}",
            teacher_label="",
            teacher_assessment_score_out_of_10="7",
            teacher_label_source_status="TEACHER_SCORE_ONLY_LEVEL_NOT_PROVIDED",
            suggested_level_unverified="intermediate",
        )
        originals.append({key: row[key] for key in FIELDS[:9]})
        rows.append(row)
    return rows, {"read_only_rows": originals}


def test_assessment_input_covers_all16_dates_and_preserves_raw_status(fixture):
    rows, snapshot = assessment_sheet()
    baseline = fixture[2].model_copy(deep=True)
    baseline.teacher_scores = {}
    assessments, report = validate_assessments(
        rows, rows, snapshot, "0" * 64, baseline, {}
    )
    assert len(assessments) == 16
    assert assessments["STU_007"].assessed_on == date(2026, 10, 15)
    assert assessments["STU_008"].assessed_on == date(2026, 10, 16)
    assert all(item.assessed_at is None for item in assessments.values())
    assert all(item.revision_before_assessment is None for item in assessments.values())
    assert report["classification_source_counts"] == {
        "TEACHER_SCORE_RUBRIC_DERIVED": 16
    }


def test_disagreeing_repeated_scores_and_review_decisions_rejected(fixture):
    rows, snapshot = assessment_sheet()
    latest = copy.deepcopy(rows)
    baseline = fixture[2].model_copy(deep=True)
    baseline.teacher_scores = {}
    extra = {
        **rows[0],
        "game_session_id": "SYNTHETIC-extra",
        "teacher_assessment_score_out_of_10": "8",
    }
    rows.append(extra)
    latest.append(extra)
    snapshot["read_only_rows"].append({key: extra[key] for key in FIELDS[:9]})
    with pytest.raises(ValueError, match="Conflicting repeated"):
        validate_assessments(rows, latest, snapshot, "0" * 64, baseline, {})
    rows[-1]["teacher_assessment_score_out_of_10"] = "7"
    rows[1]["researcher_decision"] = "UNKNOWN"
    with pytest.raises(ValueError, match="decisions conflict"):
        validate_assessments(rows, latest, snapshot, "0" * 64, baseline, {})


def shift_fixture(tables, days):
    for rows in tables.values():
        for row in rows:
            for key in ("started_at", "completed_at", "event_timestamp"):
                if row.get(key):
                    row[key] = (at(row[key]) + timedelta(days=days)).isoformat()


def prepared(fixture):
    tables, provenance, review = fixture
    return prepare_datasets(
        tables,
        provenance,
        review,
        {"STU_006": assessment(), "STU_007": assessment("STU_007", 4, "beginner")},
        {row["game_session_id"] for row in tables["game_sessions"]},
    )


@pytest.mark.parametrize(
    "days,prospective_count,category",
    [(-1, 2, BEFORE), (0, 0, SAME_DAY), (1, 0, AFTER)],
)
def test_paired_cohorts_keep_same_day_and_later_games_retrospective_only(
    fixture, days, prospective_count, category
):
    shift_fixture(fixture[0], days)
    before = copy.deepcopy(fixture)
    datasets, _, (decisions, _) = prepared(fixture)
    assert fixture == before
    assert len(datasets["retrospective"]["observations"]) == 2
    assert len(datasets["prospective"]["observations"]) == prospective_count
    assert all(row["assessment_timing_category"] == category for row in decisions)
    for purpose, dataset in datasets.items():
        assert dataset["features"]["score_only"] == [
            {key: row[key] for key in ("student_code", "session_id", "gameplay_score")}
            for row in dataset["features"]["score_plus_behaviour"]
        ]
        for row in dataset["observations"]:
            assert (
                row["assessment_phase"]
                == row["mastery_label"]["assessment_phase"]
                == "pre_tutor"
            )
            assert row["mastery_label"]["assessed_at"] is None
            assert (
                f"analysis_purpose={purpose}"
                in row["mastery_label"]["source_reference"]
            )
            if category == SAME_DAY:
                assert row["mastery_label"]["assessment_timing"] is None
            if category == AFTER:
                assert row["mastery_label"]["assessment_timing"] == "before_gameplay"


def test_retrospective_does_not_infer_post_tutor_or_claim_unknown_revision(fixture):
    tables, _, review = fixture
    shift_fixture(tables, 1)
    session = tables["game_sessions"][0]
    sid = session["game_session_id"]
    linked = [
        [row for row in tables[name] if row["game_session_id"] == sid]
        for name in ("student_answers", "game_events", "game_analytics")
    ]
    row, _ = prepare_session(
        session,
        *linked,
        review,
        independent_assessment=assessment(),
        analysis_purpose="retrospective",
    )
    assert row.assessment_phase == "pre_tutor"
    assert row.mastery_label.revision_before_assessment is None
    with pytest.raises(ValueError, match="after the recorded"):
        prepare_session(session, *linked, review)
    with pytest.raises(ValueError, match="Not demonstrably before"):
        prepare_session(
            session,
            *linked,
            review,
            independent_assessment=assessment(),
            analysis_purpose="prospective",
        )
    with pytest.raises(ValueError, match="explicit analysis purpose"):
        prepare_session(session, *linked, review, independent_assessment=assessment())


def test_authenticity_does_not_override_quarantine_and_global_integrity(fixture):
    tables, _, _ = fixture
    tables["game_analytics"][0].update(
        student_code="STU_007", student_id_recorded="STU_007"
    )
    datasets, integrity, (decisions, _) = prepared(fixture)
    assert integrity["quarantine"]["session_ids"] == ["SYNTHETIC-session-6"]
    assert len(datasets["retrospective"]["observations"]) == 1
    assert decisions[0]["researcher_verified"]
    assert decisions[0]["integrity_quarantined"]
    assert decisions[0]["exclusion_reason"] == "QUARANTINED_INTEGRITY"
    tables["game_events"][0]["source_event_id"] = tables["game_events"][1][
        "source_event_id"
    ]
    datasets, integrity, _ = prepared(fixture)
    assert integrity["global_issues"]
    assert not datasets["retrospective"]["observations"]
    assert not datasets["prospective"]["observations"]


def test_verified_incomplete_is_visible_but_excluded(fixture):
    tables, _, _ = fixture
    tables["game_sessions"][0].update(
        status="in_progress", completed_at="", saved_assessment_complete="False"
    )
    datasets, _, (decisions, _) = prepared(fixture)
    assert len(datasets["retrospective"]["observations"]) == 1
    assert decisions[0]["exclusion_reason"] == "INCOMPLETE"
    assert decisions[0]["timing_basis"] == "start date only; incomplete"


def test_completed_evidence_failure_still_blocks_training_of_remaining_cohort(fixture):
    fixture[0]["student_answers"][0]["expected_response"] = (
        "invented incorrect expected answer"
    )
    datasets, integrity, (decisions, _) = prepared(fixture)
    assert len(datasets["retrospective"]["observations"]) == 1
    config = ExperimentConfig(
        target="mastery", class_labels=("beginner", "intermediate", "advanced")
    )
    result = readiness(datasets["retrospective"], config, integrity, decisions)
    assert result["mechanical_evaluation_status"] == "BLOCKED"
    assert (
        "Some completed verified sessions failed source evidence checks"
        in result["blocking_reasons"]
    )


def test_targets_and_provenance_cannot_enter_feature_allowlists(fixture):
    datasets, _, _ = prepared(fixture)
    data = datasets["retrospective"]
    for feature_rows in data["features"].values():
        for row in feature_rows:
            assert not {
                "assessment_score",
                "teacher_score",
                "assessed_on",
                "target_level",
                "mastery_label",
                "classification_source",
                "original_source_status",
            } & set(row)
    assert paired_dataset(data["observations"])["features"] == data["features"]


def test_actual_recorded_post_tutor_phase_is_preserved(fixture):
    for rows in fixture[0].values():
        for row in rows:
            if "assessment_phase" in row:
                row["assessment_phase"] = "post_tutor"
    datasets, _, _ = prepared(fixture)
    assert all(
        row["assessment_phase"] == "post_tutor"
        for row in datasets["retrospective"]["observations"]
    )


def test_preparation_is_offline_no_fit_and_creates_immutable_hash_snapshot(
    fixture, tmp_path, monkeypatch
):
    """A complete invented export exercises the real command's guarded import."""
    import joblib
    import psycopg
    from sklearn.pipeline import Pipeline

    def forbidden(*args, **kwargs):
        raise AssertionError("No fitting, model serialization or DB connections")

    monkeypatch.setattr(Pipeline, "fit", forbidden)
    monkeypatch.setattr(joblib, "dump", forbidden)
    monkeypatch.setattr(psycopg, "connect", forbidden)
    tables, provenance, review = fixture
    for number in [*range(1, 6), *range(8, 17)]:
        code = f"STU_{number:03}"
        tables["game_sessions"].append(
            {
                **tables["game_sessions"][0],
                "game_session_id": f"SYNTHETIC-incomplete-{number}",
                "source_session_uuid": f"SYNTHETIC-extra-uuid-{number}",
                "student_code": code,
                "student_id_recorded": code,
                "status": "in_progress",
                "completed_at": "",
                "saved_assessment_complete": "False",
            }
        )
    provenance["manifest"]["counts"]["game_sessions"] = 16
    export = tmp_path / "SYNTHETIC-export.zip"
    with ZipFile(export, "w") as archive:
        for name, rows in tables.items():
            buffer = io.StringIO(newline="")
            headers = list(dict.fromkeys(key for row in rows for key in row))
            writer = csv.DictWriter(buffer, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
            archive.writestr(name + ".csv", buffer.getvalue())
        archive.writestr("manifest.json", json.dumps(provenance["manifest"]))
    from app.modules.game.ml.collection_research import read_export

    tables, provenance = read_export(export)
    original = tmp_path / "SYNTHETIC-original"
    generate_sheet(tables, provenance, review, original)
    sheet = original / "session_review_sheet.csv"
    rows = read_sheet(sheet, FIELDS)
    assessment_rows = [
        {
            **row,
            "teacher_assessment_score_out_of_10": "4"
            if row["student_code"] == "STU_007"
            else "7",
            "teacher_label_source_status": "DOCUMENTED_TEACHER_LEVEL"
            if row["teacher_label"]
            else "TEACHER_SCORE_ONLY_LEVEL_NOT_PROVIDED",
            "suggested_level_unverified": "",
        }
        for row in rows
    ]
    assessments = tmp_path / "SYNTHETIC-teacher.csv"
    write_csv(assessments, assessment_rows, (*FIELDS, *ASSESSMENT_FIELDS))
    inputs = [
        export,
        sheet,
        assessments,
        original / "review_snapshot.json",
        original / "review_baseline.json",
    ]
    hashes = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs
    }
    output = tmp_path / "SYNTHETIC-preparation"
    kwargs = dict(
        export=export,
        sheet=sheet,
        assessment_csv=assessments,
        snapshot_path=inputs[3],
        baseline_path=inputs[4],
        output=output,
    )
    result = prepare(**kwargs)
    assert result["input_hashes_unchanged"]
    assert result["readiness"]["retrospective"]["model_a_observations"] == 2
    assert result["readiness"]["prospective"]["model_a_observations"] == 0
    assert hashes == {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs
    }
    manifest = json.loads((output / "snapshot_manifest.json").read_text())
    assert manifest["complete"]
    assert not manifest["models_trained"]
    for name, checksum in manifest["files_sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == checksum
    with pytest.raises(FileExistsError, match="snapshot exists"):
        prepare(**kwargs)
    assert not list(output.rglob("*.joblib"))
    assert not list(output.rglob("*.pkl"))
