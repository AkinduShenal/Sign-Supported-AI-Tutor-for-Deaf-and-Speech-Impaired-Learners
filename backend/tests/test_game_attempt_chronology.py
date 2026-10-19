"""Invented engineering evidence only. No real approvals, targets or fitting."""

import copy
from itertools import permutations

import pytest

from app.modules.game.ml.collection_research import audit_attempt_chronology
from app.modules.game.ml.assessment_preparation import prepare_datasets
from test_game_assessment_preparation import assessment

pytest_plugins = ["test_game_collection_research"]


def case():
    def event(kind, number, second, suffix):
        return {
            "source_event_id": f"SYNTHETIC-source-{suffix}",
            "client_event_id": f"SYNTHETIC-client-{suffix}",
            "game_session_id": "SYNTHETIC-session",
            "student_id_recorded": "STU_006",
            "task_id": "SYNTHETIC-task",
            "step_index": "0",
            "attempt_number": str(number) if number else "",
            "event_type": kind,
            "event_timestamp": f"2026-10-15T09:00:0{second}+00:00",
        }

    rows = [
        event("ANSWER_INCORRECT", 1, 2, "outcome-1"),
        event("ANSWER_CORRECT", 3, 4, "outcome-3"),
        event("ANSWER_INCORRECT", 2, 4, "outcome-2"),
    ]
    events = [
        event("QUESTION_SHOWN", None, 0, "shown"),
        event("ANSWER_SUBMITTED", 1, 1, "submit-1"),
        event("ANSWER_SUBMITTED", 2, 3, "submit-2"),
        event("ANSWER_SUBMITTED", 3, 4, "submit-3"),
        *copy.deepcopy(rows),
        event("TASK_COMPLETED", None, 5, "complete"),
    ]
    return rows, events


@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_equal_timestamps_use_recorded_counter_not_csv_or_uuid_order(order):
    rows, events = case()
    rows = [rows[i] for i in order]
    before = copy.deepcopy((rows, events))
    decision = audit_attempt_chronology(rows, events, "drag_drop")
    assert decision["decision"] == "ACCEPT_RECORDED_LOGICAL_SEQUENCE"
    assert decision["recorded_logical_attempt_order"] == [1, 2, 3]
    assert decision["original_exported_outcome_attempt_order"] == [
        int(row["attempt_number"]) for row in rows
    ]
    assert decision["tied_attempt_groups"][0]["attempt_numbers"] == [2, 3]
    assert (
        decision["wall_clock_order_within_ties"] == "UNRESOLVED_AT_RECORDED_PRECISION"
    )
    assert not decision["source_rows_modified"]
    assert (rows, events) == before


def test_equal_timestamps_without_independent_submission_evidence_remain_blocked():
    rows, events = case()
    events = [r for r in events if r["event_type"] != "ANSWER_SUBMITTED"]
    with pytest.raises(ValueError, match="complete unique numbered submission"):
        audit_attempt_chronology(rows, events, "drag_drop")


@pytest.mark.parametrize("change", ["missing", "duplicate", "zero", "noninteger"])
def test_bad_attempt_numbers_are_not_reconstructed(change):
    rows, events = case()
    rows[0]["attempt_number"] = {
        "missing": "",
        "duplicate": "2",
        "zero": "0",
        "noninteger": "1.5",
    }[change]
    with pytest.raises(ValueError):
        audit_attempt_chronology(rows, events, "drag_drop")


@pytest.mark.parametrize("field", ["source_event_id", "client_event_id"])
@pytest.mark.parametrize("invalid", ["duplicate", "missing"])
def test_tie_evidence_requires_distinct_nonempty_identities(field, invalid):
    rows, events = case()
    submitted = next(r for r in events if r["event_type"] == "ANSWER_SUBMITTED")
    submitted[field] = rows[0][field] if invalid == "duplicate" else ""
    with pytest.raises(ValueError, match="distinct nonempty"):
        audit_attempt_chronology(rows, events, "drag_drop")


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_submission_number",
        "missing_submission_number",
        "missing_submission",
        "cross_session",
        "cross_learner",
    ],
)
def test_tie_corroboration_cannot_be_missing_or_borrowed(change):
    rows, events = case()
    submissions = [r for r in events if r["event_type"] == "ANSWER_SUBMITTED"]
    if change == "duplicate_submission_number":
        submissions[1]["attempt_number"] = "1"
    elif change == "missing_submission_number":
        submissions[1]["attempt_number"] = ""
    elif change == "missing_submission":
        events.remove(submissions[1])
    elif change == "cross_session":
        submissions[1]["game_session_id"] = "SYNTHETIC-other"
    else:
        submissions[1]["student_id_recorded"] = "STU_007"
    with pytest.raises(ValueError):
        audit_attempt_chronology(rows, events, "drag_drop")


def test_strictly_reversed_outcomes_are_still_errors():
    rows, events = case()
    rows[1]["event_timestamp"] = "2026-10-15T09:00:01+00:00"  # attempt 3 before 2
    with pytest.raises(ValueError, match="contradicts event chronology"):
        audit_attempt_chronology(rows, events, "drag_drop")


@pytest.mark.parametrize(
    "change", ["submitted_after_outcome", "next_submission_before_prior_outcome"]
)
def test_true_submission_sequence_inversions_are_not_hidden_by_ties(change):
    rows, events = case()
    submitted = next(
        r
        for r in events
        if r["event_type"] == "ANSWER_SUBMITTED" and r["attempt_number"] == "2"
    )
    submitted["event_timestamp"] = (
        "2026-10-15T09:00:05+00:00"
        if change == "submitted_after_outcome"
        else "2026-10-15T09:00:01+00:00"
    )
    with pytest.raises(ValueError, match="submission/outcome sequence contradicts"):
        audit_attempt_chronology(rows, events, "drag_drop")


@pytest.mark.parametrize(
    "kind,second", [("QUESTION_SHOWN", 3), ("TASK_COMPLETED", 3), ("HINT_REQUESTED", 4)]
)
def test_hint_or_boundary_ambiguity_cannot_create_complete_model_b_features(
    kind, second
):
    rows, events = case()
    event = next(
        r
        for r in events
        if r["event_type"] == (kind if kind != "HINT_REQUESTED" else "QUESTION_SHOWN")
    )
    if kind == "HINT_REQUESTED":
        event = {
            **event,
            "event_type": kind,
            "source_event_id": "SYNTHETIC-hint",
            "client_event_id": "SYNTHETIC-hint-client",
        }
        events.append(event)
    event["event_timestamp"] = f"2026-10-15T09:00:0{second}+00:00"
    with pytest.raises(ValueError):
        audit_attempt_chronology(rows, events, "drag_drop")


def test_no_tie_keeps_existing_chronology_requirements():
    rows, _ = case()
    rows[1]["event_timestamp"] = "2026-10-15T09:00:05+00:00"
    assert audit_attempt_chronology(rows, [], "drag_drop") is None


def add_tied_attempts(fixture):
    tables, provenance, _ = fixture
    original = tables["student_answers"][0]
    original.update(
        submitted_answer="-1", is_correct="False", first_attempt_correct="False"
    )
    outcome = next(
        r
        for r in tables["game_events"]
        if r["source_event_id"] == original["source_event_id"]
    )
    outcome["event_type"] = "ANSWER_INCORRECT"
    for number in (3, 2):
        result = {
            **outcome,
            "source_event_id": f"SYNTHETIC-extra-outcome-{number}",
            "client_event_id": f"SYNTHETIC-extra-client-{number}",
            "event_type": "ANSWER_CORRECT" if number == 3 else "ANSWER_INCORRECT",
            "attempt_number": str(number),
            "event_timestamp": "2026-10-15T09:00:04+00:00",
        }
        tables["game_events"].append(result)
        tables["student_answers"].append(
            {
                **original,
                **result,
                "submitted_answer": "+1" if number == 3 else "-1",
                "is_correct": "True" if number == 3 else "False",
            }
        )
        tables["game_events"].append(
            {
                **result,
                "event_type": "ANSWER_SUBMITTED",
                "source_event_id": f"SYNTHETIC-extra-submit-{number}",
                "client_event_id": f"SYNTHETIC-extra-submit-client-{number}",
            }
        )
        tables["game_events"].append(
            {
                **result,
                "event_type": "RETRY_STARTED",
                "source_event_id": f"SYNTHETIC-extra-retry-{number}",
                "client_event_id": f"SYNTHETIC-extra-retry-client-{number}",
            }
        )
    tables["game_analytics"][0].update(wrong_attempt_count="2", retry_count="2")
    provenance["manifest"]["counts"]["student_answers"] += 2
    provenance["manifest"]["counts"]["source_gameplay_events"] += 6


def prepared(fixture):
    tables, provenance, review = fixture
    return prepare_datasets(
        tables,
        provenance,
        review,
        {"STU_006": assessment(), "STU_007": assessment("STU_007", 4, "beginner")},
        {r["game_session_id"] for r in tables["game_sessions"]},
    )


def test_tied_complete_session_preserves_first_attempt_scoring_and_paired_feature_integrity(
    fixture,
):
    add_tied_attempts(fixture)
    before = copy.deepcopy(fixture)
    datasets, _, (_, links) = prepared(fixture)
    assert fixture == before
    data = datasets["retrospective"]
    row = next(r for r in data["observations"] if r["student_code"] == "STU_006")
    assert row["first_attempt_correct_steps"] == 5 and row["total_steps"] == 6
    assert row["gameplay_score"] == 5 / 6
    assert row["wrong_attempts"] == row["retry_count"] == 2
    assert row["hint_count"] == row["skipped_steps"] == 0
    assert row["tasks_completed"] == 6 and row["task_completed"]
    assert row["task_duration_seconds"] is None and not row["task_duration_reliable"]
    assert len(data["observations"]) == 2
    assert [r["session_id"] for r in data["features"]["score_only"]] == [
        r["session_id"] for r in data["features"]["score_plus_behaviour"]
    ]
    assert links[0]["attempt_chronology_decisions"][0][
        "original_exported_outcome_attempt_order"
    ] == [1, 3, 2]
    assert not datasets["prospective"]["observations"]  # same-day rules unchanged


def test_tie_policy_cannot_override_ownership_quarantine(fixture):
    add_tied_attempts(fixture)
    fixture[0]["game_analytics"][0].update(
        student_code="STU_007", student_id_recorded="STU_007"
    )
    datasets, integrity, (decisions, _) = prepared(fixture)
    assert integrity["quarantine"]["session_ids"] == ["SYNTHETIC-session-6"]
    assert len(datasets["retrospective"]["observations"]) == 1
    assert decisions[0]["exclusion_reason"] == "QUARANTINED_INTEGRITY"


def test_tie_policy_cannot_admit_an_unrecognized_recording_protocol(fixture):
    add_tied_attempts(fixture)
    fixture[0]["game_sessions"][0]["recording_protocol"] = "SYNTHETIC-unknown-protocol"
    datasets, _, (decisions, _) = prepared(fixture)
    assert len(datasets["retrospective"]["observations"]) == 1
    assert "Need audited recording protocol" in decisions[0]["exclusion_reason"]
