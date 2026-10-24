"""Versioned CSV contracts for independent Quiz misconception research."""

from __future__ import annotations

from dataclasses import dataclass

TAXONOMY_VERSION = "m3a-taxonomy-v1-proposed"
FORM_VERSION = "m3a-independent-v1-proposed"
CATEGORIES = frozenset({"M0", "M1", "M2", "M3", "M4", "REVIEW"})
TARGET_CATEGORIES = CATEGORIES - {"REVIEW"}
OPTION_TAGS = frozenset(
    {"", "inverse_operation", "sign_error", "arithmetic_error", "concept_confusion"}
)
ORIGINS = frozenset({"real", "synthetic", "development_test", "unverified"})
REVIEW_STATUSES = frozenset({"pending", "approved", "rejected"})
EVIDENCE_STATUSES = frozenset({"pending", "verified", "rejected"})


@dataclass(frozen=True)
class CsvSchema:
    columns: tuple[str, ...]
    identifier: str


SCHEMAS = {
    "00_proposed_taxonomy.csv": CsvSchema(
        (
            "taxonomy_version",
            "category_code",
            "name",
            "definition",
            "example_error",
            "positive_criteria",
            "exclusion_criteria",
            "minimum_evidence",
            "possible_overlap",
            "teacher_review_status",
            "approval_reference",
        ),
        "category_code",
    ),
    "01_teacher_assessment_items.csv": CsvSchema(
        (
            "form_version",
            "item_id",
            "concept_id",
            "subconcept_code",
            "prompt_en",
            "prompt_si",
            "expected_working",
            "opportunity_codes",
            "working_steps_required",
            "hints_or_feedback_allowed",
            "teacher_review_status",
            "approval_reference",
        ),
        "item_id",
    ),
    "02_teacher_assessment_sessions.csv": CsvSchema(
        (
            "assessment_id",
            "quiz_session_id",
            "student_code",
            "form_version",
            "assessment_started_at",
            "assessment_completed_at",
            "tutoring_status",
            "tutoring_started_at",
            "no_hints_or_feedback",
            "assessor_code",
            "assessor_blinded_to_quiz",
            "record_origin",
            "research_authorized",
            "authorization_reference",
            "consent_evidence_reference",
        ),
        "assessment_id",
    ),
    "03_teacher_item_evidence.csv": CsvSchema(
        (
            "evidence_id",
            "assessment_id",
            "item_id",
            "rater_code",
            "recorded_at",
            "working_steps",
            "observed_error",
            "proposed_category",
            "verification_status",
            "evidence_quality",
            "notes",
        ),
        "evidence_id",
    ),
    "04_teacher_consensus_labels.csv": CsvSchema(
        (
            "label_id",
            "assessment_id",
            "quiz_session_id",
            "student_code",
            "form_version",
            "taxonomy_version",
            "consensus_category",
            "verification_status",
            "consensus_method",
            "rater_codes",
            "disagreement_flag",
            "evidence_ids",
            "resolution_note",
            "verified_by_code",
            "verified_at",
        ),
        "label_id",
    ),
    "05_quiz_ml_features.csv": CsvSchema(
        (
            "quiz_session_id",
            "student_code",
            "concept_id",
            "quiz_completed_at",
            "question_count",
            "correct_count",
            "accuracy",
            "response_time_mean_sec",
            "response_time_median_sec",
            "confidence_low_count",
            "confidence_medium_count",
            "confidence_high_count",
            "high_confidence_wrong_count",
            "easy_correct_count",
            "medium_correct_count",
            "hard_correct_count",
            "easy_question_count",
            "medium_question_count",
            "hard_question_count",
            "option_inverse_operation_count",
            "option_sign_error_count",
            "option_arithmetic_error_count",
            "option_concept_confusion_count",
        ),
        "quiz_session_id",
    ),
    "06_quiz_ml_labeled_dataset.csv": CsvSchema(
        (
            "quiz_session_id",
            "student_code",
            "assessment_id",
            "label_id",
            "concept_id",
            "quiz_completed_at",
            "assessment_completed_at",
            "taxonomy_version",
            "form_version",
            "teacher_category",
        )
        + (
            "question_count",
            "correct_count",
            "accuracy",
            "response_time_mean_sec",
            "response_time_median_sec",
            "confidence_low_count",
            "confidence_medium_count",
            "confidence_high_count",
            "high_confidence_wrong_count",
            "easy_correct_count",
            "medium_correct_count",
            "hard_correct_count",
            "easy_question_count",
            "medium_question_count",
            "hard_question_count",
            "option_inverse_operation_count",
            "option_sign_error_count",
            "option_arithmetic_error_count",
            "option_concept_confusion_count",
        ),
        "label_id",
    ),
}

# These are join/provenance metadata, never model input columns.
FEATURE_METADATA = frozenset(
    {"quiz_session_id", "student_code", "concept_id", "quiz_completed_at"}
)
PREDICTOR_COLUMNS = tuple(
    column
    for column in SCHEMAS["05_quiz_ml_features.csv"].columns
    if column not in FEATURE_METADATA
)

SOURCE_SESSION_COLUMNS = frozenset(
    {
        "source_session_id",
        "quiz_session_id",
        "student_id_recorded",
        "student_code",
        "concept_id",
        "learning_cycle_id",
        "assessment_phase",
        "quiz_attempt_number",
        "status",
        "assessment_complete",
        "responses_saved",
        "started_at",
        "completed_at",
    }
)
SOURCE_RESPONSE_COLUMNS = frozenset(
    {
        "source_response_id",
        "quiz_session_id",
        "student_id_recorded",
        "student_code",
        "assessment_phase",
        "assessment_complete",
        "question_id",
        "question_code",
        "question_order",
        "concept_id",
        "subconcept_code",
        "difficulty_level",
        "selected_option_id",
        "is_correct",
        "response_time_sec",
        "confidence_level",
        "misconception_code",
        "answered_at",
        "saved_at",
    }
)
