"""Synthetic engineering review decisions only; no real authenticity assertions."""

import copy
import csv
import json

import pytest
from pydantic import ValidationError

from test_game_collection_research import fixture as source_fixture  # noqa: F401

from app.modules.game.ml.collection_research import (
    CLASSES,
    DEVELOPMENT_SESSIONS,
    INVALID_CODE_DECISION,
    CollectionReview,
    audit_collection,
)
from app.modules.game.ml.research_training import ExperimentConfig
from app.modules.game.ml.session_verification import (
    FIELDS,
    apply_sheet,
    generate_sheet,
    import_decisions,
    review_rows,
)


@pytest.fixture
def case(request, tmp_path):
    tables, provenance, baseline = request.getfixturevalue("source_fixture")
    original = copy.deepcopy(tables)
    # One unverified complete session and one unverified incomplete session.
    for name, rows in original.items():
        for source in rows:
            if source["game_session_id"] != "SYNTHETIC-session-6":
                continue
            row = {
                **source,
                "game_session_id": "GAME-SES-2026-004",
                "student_id_recorded": "STU_003",
            }
            if "student_code" in row:
                row["student_code"] = "STU_003"
            for key in (
                "source_event_id",
                "client_event_id",
                "source_result_id",
                "source_session_uuid",
            ):
                if key in row:
                    row[key] += "-unknown"
            tables[name].append(row)
    incomplete = {
        **tables["game_sessions"][0],
        "game_session_id": "SYNTHETIC-incomplete",
        "source_session_uuid": "SYNTHETIC-incomplete-uuid",
        "student_code": "STU_001",
        "student_id_recorded": "STU_001",
        "status": "in_progress",
        "completed_at": "",
        "saved_assessment_complete": "False",
    }
    tables["game_sessions"].append(incomplete)
    for index, sid in enumerate(sorted(DEVELOPMENT_SESSIONS)):
        tables["game_sessions"].append(
            {
                **incomplete,
                "game_session_id": sid,
                "student_code": "",
                "student_id_recorded": f"SYNTHETIC-legacy-{index}",
                "source_session_uuid": f"SYNTHETIC-dev-uuid-{index}",
            }
        )
    baseline.teacher_scores.update({"STU_001": 3, "STU_003": 5})
    provenance["manifest"]["counts"] = {
        "game_sessions": 7,
        "student_answers": 18,
        "source_gameplay_events": 78,
        "game_analytics": 3,
    }
    provenance["file_sha256"] = {"SYNTHETIC-export": "0" * 64}
    folder = tmp_path / "SYNTHETIC-sheet"
    generate_sheet(tables, provenance, baseline, folder)
    snapshot = json.loads((folder / "review_snapshot.json").read_text())
    return tables, provenance, baseline, folder, snapshot


def sheet_rows(case):
    with (case[3] / "session_review_sheet.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        return list(csv.DictReader(stream))


def edit(case, rows):
    sheet = case[3] / "session_review_sheet.csv"
    with sheet.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return sheet


def imported(case):
    tables, provenance, baseline, folder, snapshot = case
    return import_decisions(
        folder / "session_review_sheet.csv", snapshot, tables, provenance, baseline
    )


def test_defaults_preserve_only_previously_confirmed_decisions(case):
    rows = sheet_rows(case)
    decisions = {row["game_session_id"]: row["researcher_decision"] for row in rows}
    assert (
        decisions["SYNTHETIC-session-6"]
        == decisions["SYNTHETIC-session-7"]
        == "RESEARCH_VERIFIED"
    )
    assert (
        decisions["GAME-SES-2026-004"] == decisions["SYNTHETIC-incomplete"] == "UNKNOWN"
    )
    assert all(decisions[sid] == "DEVELOPMENT_TEST" for sid in DEVELOPMENT_SESSIONS)
    assert all(tuple(row) == FIELDS for row in rows)
    reviewed, receipt = imported(case)
    assert set(reviewed.verified_sessions) == set(case[2].verified_sessions)
    assert receipt["review_sheet_counts"] == {
        "DEVELOPMENT_TEST": 3,
        "UNKNOWN": 2,
        "RESEARCH_VERIFIED": 2,
    }


def test_explicit_verification_adds_only_that_source_session(case):
    rows = sheet_rows(case)
    row = next(row for row in rows if row["game_session_id"] == "GAME-SES-2026-004")
    row.update(
        researcher_decision="RESEARCH_VERIFIED",
        verification_basis="SYNTHETIC researcher collection-log entry",
        review_notes="SYNTHETIC observation confirmation",
    )
    edit(case, rows)
    before = copy.deepcopy(case[0])
    reviewed, receipt = imported(case)
    result = audit_collection(case[0], case[1], reviewed)
    assert len(result["observations"]) == 3
    assert {row["student_code"] for row in result["observations"]} == {
        "STU_003",
        "STU_006",
        "STU_007",
    }
    assert result["learner_class_distribution"] == {
        "beginner": 1,
        "intermediate": 2,
        "advanced": 0,
    }
    assert case[0] == before
    assert any(
        row["review_notes"] == "SYNTHETIC observation confirmation"
        for row in receipt["decisions"]
    )


@pytest.mark.parametrize("prior_approval", [False, True])
def test_invalid_code_is_visible_and_cannot_be_reapproved(case, tmp_path, prior_approval):
    tables, provenance, baseline, _, _ = case
    sid = "SYNTHETIC-session-6"
    for rows in tables.values():
        for row in rows:
            if row["game_session_id"] == sid:
                row["student_id_recorded"] = "STU_0014"
                if "student_code" in row:
                    row["student_code"] = "STU_0014"
    baseline.verified_sessions[sid].student_code = "STU_0014"
    if not prior_approval:
        baseline.verified_sessions.pop(sid)
    before = copy.deepcopy(tables)
    folder = tmp_path / "SYNTHETIC-invalid-sheet"
    generate_sheet(tables, provenance, baseline, folder)
    snapshot = json.loads((folder / "review_snapshot.json").read_text())
    invalid_case = tables, provenance, baseline, folder, snapshot
    rows = sheet_rows(invalid_case)
    invalid = next(row for row in rows if row["game_session_id"] == sid)
    assert invalid["student_code"] == "STU_0014"
    assert invalid["researcher_decision"] == INVALID_CODE_DECISION
    reviewed, _ = imported(invalid_case)
    assert sid not in reviewed.verified_sessions
    assert set(reviewed.verified_sessions) == {"SYNTHETIC-session-7"}
    assert tables == before
    invalid["researcher_decision"] = "RESEARCH_VERIFIED"
    edit(invalid_case, rows)
    with pytest.raises(ValueError, match="Invalid student-code exclusion must be preserved"):
        imported(invalid_case)


def test_valid_code_cannot_be_marked_as_accidental_entry(case):
    rows = sheet_rows(case)
    row = next(row for row in rows if row["game_session_id"] == "GAME-SES-2026-004")
    row.update(researcher_decision=INVALID_CODE_DECISION, verification_basis="SYNTHETIC")
    edit(case, rows)
    with pytest.raises(ValueError, match="does not record an excluded invalid code"):
        imported(case)


def test_expanded_roster_is_reviewed_without_inventing_labels(case):
    tables, provenance, baseline, _, _ = case
    for number in range(8, 17):
        tables["game_sessions"].append(
            {
                **tables["game_sessions"][0],
                "game_session_id": f"SYNTHETIC-candidate-{number}",
                "student_code": f"STU_{number:03}",
                "student_id_recorded": f"STU_{number:03}",
            }
        )
    provenance["manifest"]["counts"]["game_sessions"] = len(tables["game_sessions"])
    rows = review_rows(tables, provenance, baseline)
    candidates = [row for row in rows if row["game_session_id"].startswith("SYNTHETIC-candidate-")]
    assert len(candidates) == 9
    assert all(row["researcher_decision"] == "UNKNOWN" for row in candidates)
    assert all(row["teacher_label"] == "" for row in candidates)


def test_quarantine_does_not_invent_or_remove_authenticity_decisions(case, tmp_path):
    tables, provenance, baseline, _, _ = case
    next(
        row for row in tables["game_analytics"]
        if row["game_session_id"] == "GAME-SES-2026-004"
    ).update(student_id_recorded="STU_012", student_code="STU_012")
    before = copy.deepcopy(tables)
    folder = tmp_path / "SYNTHETIC-quarantined-sheet"
    generate_sheet(tables, provenance, baseline, folder)
    snapshot = json.loads((folder / "review_snapshot.json").read_text())
    new_case = tables, provenance, baseline, folder, snapshot
    row = next(row for row in sheet_rows(new_case) if row["game_session_id"] == "GAME-SES-2026-004")
    assert row["researcher_decision"] == "UNKNOWN"
    assert row["existing_verification_status"] == "QUARANTINED_INTEGRITY"
    output = tmp_path / "SYNTHETIC-quarantine-import"
    result = apply_sheet(
        folder / "session_review_sheet.csv", snapshot, tables, provenance, baseline,
        ExperimentConfig(target="mastery", class_labels=CLASSES), output,
    )
    reviewed = json.loads((output / "review_input.json").read_text())
    assert reviewed["verified_sessions"] == baseline.model_dump(mode="json")["verified_sessions"]
    assert result["audit_summary"]["eligible_sessions"] == 2
    assert result["review_sheet_counts"]["UNKNOWN"] == 2
    assert tables == before


def test_old_smaller_sheet_cannot_be_imported_into_expanded_snapshot(case, tmp_path):
    tables, provenance, baseline, old_folder, _ = case
    tables["game_sessions"].append({
        **tables["game_sessions"][0],
        "game_session_id": "SYNTHETIC-new-candidate",
        "source_session_uuid": "SYNTHETIC-new-candidate-uuid",
        "student_code": "STU_016", "student_id_recorded": "STU_016",
    })
    provenance["manifest"]["counts"]["game_sessions"] += 1
    folder = tmp_path / "SYNTHETIC-expanded-sheet"
    generate_sheet(tables, provenance, baseline, folder)
    snapshot = json.loads((folder / "review_snapshot.json").read_text())
    with pytest.raises(ValueError, match="omits original session rows"):
        import_decisions(
            old_folder / "session_review_sheet.csv", snapshot, tables, provenance, baseline
        )


def test_additional_development_decision_excludes_exact_id_only(case):
    rows = sheet_rows(case)
    row = next(row for row in rows if row["game_session_id"] == "GAME-SES-2026-004")
    row.update(
        researcher_decision="DEVELOPMENT_TEST",
        verification_basis="SYNTHETIC researcher test log",
    )
    edit(case, rows)
    reviewed, _ = imported(case)
    result = audit_collection(case[0], case[1], reviewed)
    decisions = {row["session_id"]: row["decision"] for row in result["session_review"]}
    assert decisions["GAME-SES-2026-004"] == "EXCLUDED DEVELOPMENT"
    assert decisions["SYNTHETIC-incomplete"] == "REVIEW REQUIRED"
    assert len(result["observations"]) == 2
    assert result["summary"]["researcher_development_exclusions"] == [
        "GAME-SES-2026-004"
    ]


@pytest.mark.parametrize(
    "field,value",
    [
        ("game_session_id", "SYNTHETIC-does-not-exist"),
        ("student_code", "STU_005"),
        ("game_mode", "hangman"),
        ("answer_count", "999"),
        ("teacher_label", "advanced"),
        ("started_at", "2026-10-10"),
        ("completed_at", "2026-10-16"),
        ("completion_status", "in_progress"),
        ("existing_verification_status", "INCLUDED VERIFIED"),
    ],
)
def test_changed_source_columns_rejected(case, field, value):
    rows = sheet_rows(case)
    row = next(row for row in rows if row["game_session_id"] == "GAME-SES-2026-004")
    row[field] = value
    edit(case, rows)
    with pytest.raises(ValueError):
        imported(case)


@pytest.mark.parametrize("conflicting", [False, True])
def test_duplicate_and_conflicting_rows_rejected(case, conflicting):
    rows = sheet_rows(case)
    duplicate = copy.deepcopy(rows[0])
    if conflicting:
        duplicate["researcher_decision"] = "UNKNOWN"
    rows.append(duplicate)
    edit(case, rows)
    with pytest.raises(ValueError, match="Duplicate/conflicting"):
        imported(case)


@pytest.mark.parametrize("decision", ["", "YES", "research_verified"])
def test_invalid_decisions_rejected(case, decision):
    rows = sheet_rows(case)
    next(row for row in rows if row["game_session_id"] == "GAME-SES-2026-004")[
        "researcher_decision"
    ] = decision
    edit(case, rows)
    with pytest.raises(ValueError, match="Invalid researcher decision"):
        imported(case)


@pytest.mark.parametrize("decision", ["RESEARCH_VERIFIED", "DEVELOPMENT_TEST"])
def test_decision_requires_verification_basis(case, decision):
    rows = sheet_rows(case)
    row = next(row for row in rows if row["game_session_id"] == "GAME-SES-2026-004")
    row.update(researcher_decision=decision, verification_basis=" ")
    edit(case, rows)
    with pytest.raises(ValueError, match="verification_basis"):
        imported(case)


@pytest.mark.parametrize(
    "sid,decision",
    [("GAME-SES-2026-001", "RESEARCH_VERIFIED"), ("SYNTHETIC-session-6", "UNKNOWN")],
)
def test_previous_verified_and_development_decisions_preserved(case, sid, decision):
    rows = sheet_rows(case)
    next(row for row in rows if row["game_session_id"] == sid)[
        "researcher_decision"
    ] = decision
    edit(case, rows)
    with pytest.raises(ValueError, match="must be preserved"):
        imported(case)


def test_changed_export_baseline_snapshot_and_missing_rows_rejected(case):
    old = copy.deepcopy(case[1])
    case[1]["file_sha256"]["SYNTHETIC-export"] = "1" * 64
    with pytest.raises(ValueError, match="Source export changed"):
        imported(case)
    case[1].update(old)
    case[4]["baseline_sha256"] = "1" * 64
    with pytest.raises(ValueError, match="baseline changed"):
        imported(case)
    case[4].update(json.loads((case[3] / "review_snapshot.json").read_text()))
    edit(case, sheet_rows(case)[:-1])
    with pytest.raises(ValueError, match="omits"):
        imported(case)


def test_approved_incomplete_session_is_preserved_without_entering_training(
    case, tmp_path
):
    rows = sheet_rows(case)
    row = next(row for row in rows if row["game_session_id"] == "SYNTHETIC-incomplete")
    row.update(
        researcher_decision="RESEARCH_VERIFIED",
        verification_basis="SYNTHETIC log confirms learner; assessment unfinished",
    )
    sheet = edit(case, rows)
    output = tmp_path / "SYNTHETIC-import"
    result = apply_sheet(
        sheet,
        case[4],
        case[0],
        case[1],
        case[2],
        ExperimentConfig(target="mastery", class_labels=CLASSES),
        output,
        train=True,
    )
    assert result["eligible_observations"] == 2
    assert result["training"]["status"] == "NOT TRAINED"
    incomplete = json.loads((output / "incomplete_sessions.json").read_text())
    pending = next(
        row for row in incomplete if row["session_id"] == "SYNTHETIC-incomplete"
    )
    assert pending["decision"] == "VERIFIED / EVIDENCE BLOCKED"
    assert not (output / "experimental_models").exists()
    with pytest.raises(FileExistsError):
        apply_sheet(
            sheet,
            case[4],
            case[0],
            case[1],
            case[2],
            ExperimentConfig(target="mastery", class_labels=CLASSES),
            output,
        )


def test_generation_never_overwrites_and_conflicting_config_rejected(case):
    with pytest.raises(FileExistsError):
        generate_sheet(case[0], case[1], case[2], case[3])
    data = case[2].model_dump(mode="json")
    data["development_sessions"] = {
        "SYNTHETIC-session-6": "SYNTHETIC conflicting test decision"
    }
    with pytest.raises(ValidationError, match="conflict"):
        CollectionReview.model_validate_json(json.dumps(data))
