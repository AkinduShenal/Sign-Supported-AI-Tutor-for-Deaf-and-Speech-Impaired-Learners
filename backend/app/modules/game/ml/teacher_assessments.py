"""Date-only, independent teacher evidence for offline Milestone 2.3.3 preparation.

Original CSV annotations remain evidence, including any contradicted level. This
module never reads Game scores to construct a target and never invents a time.
"""

from datetime import date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .research_schema import IndependentLabel

RUBRIC = "simple-linear-equations-10q-beginner0-4-intermediate5-7-advanced8-10"
DATE_CONFIRMATION = (
    "Researcher confirmation, Milestone 2.3.3: separate teacher-administered "
    "mathematics assessments; STU_001-STU_007 on 2026-10-15 and "
    "STU_008-STU_016 on 2026-10-16; exact times unknown."
)
BEFORE = "BEFORE_ASSESSMENT"
SAME_DAY = "SAME_DAY_ORDERING_UNKNOWN"
AFTER = "AFTER_ASSESSMENT"
Purpose = Literal["prospective", "retrospective"]


def rubric_level(score: int) -> str:
    return "beginner" if score <= 4 else "intermediate" if score <= 7 else "advanced"


def timing_category(
    start: datetime,
    end: datetime | None,
    assessed_on: date,
    timezone: str = "Asia/Colombo",
) -> str:
    """Use the whole known window; a session spanning the date is indeterminate.

    For an unfinished session, its known start date is displayed, but it cannot
    become an eligible observation. No date-only value becomes a timestamp.
    """
    zone = ZoneInfo(timezone)
    for value in (start, end):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Game timestamps must include a timezone")
    if end is not None and end < start:
        raise ValueError("Game session ends before it starts")
    first = start.astimezone(zone).date()
    last = (end or start).astimezone(zone).date()
    if last < assessed_on:
        return BEFORE
    if first > assessed_on:
        return AFTER
    return SAME_DAY


class TeacherAssessment(BaseModel):
    """Validated evidence, not an editable assertion of its own derived label."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    student_code: Annotated[str, Field(pattern=r"^STU_(00[1-9]|01[0-6])$")]
    score: Annotated[int, Field(ge=0, le=10)]
    original_score_text: str
    assessed_on: Annotated[date, Field(strict=False)]
    assessed_at: None = None
    timezone: Literal["Asia/Colombo"] = "Asia/Colombo"
    original_teacher_level: str
    original_source_status: Literal[
        "DOCUMENTED_TEACHER_LEVEL", "TEACHER_SCORE_ONLY_LEVEL_NOT_PROVIDED"
    ]
    original_suggested_level_unverified: str
    source_csv_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    source_row_numbers: Annotated[list[int], Field(min_length=1)]
    assessment_date_reference: Literal[DATE_CONFIRMATION] = DATE_CONFIRMATION
    score_level_resolution_reference: str | None = None
    revision_before_assessment: bool | None = None
    revision_description: str | None = None

    @model_validator(mode="after")
    def evidence_consistent(self):
        if (
            not self.original_score_text.isascii()
            or not self.original_score_text.isdigit()
        ):
            raise ValueError("Original teacher score must be an integer")
        if int(self.original_score_text) != self.score:
            raise ValueError("Original teacher score changed")
        expected_date = date(2026, 10, 15 if int(self.student_code[4:]) <= 7 else 16)
        if self.assessed_on != expected_date:
            raise ValueError("Assessment date differs from researcher confirmation")
        if self.original_source_status == "DOCUMENTED_TEACHER_LEVEL":
            if self.original_teacher_level not in (
                "beginner",
                "intermediate",
                "advanced",
            ):
                raise ValueError("Documented teacher level is missing or invalid")
        elif self.original_teacher_level:
            raise ValueError("Score-only source unexpectedly includes a teacher level")
        if self.score_level_resolution_reference is not None:
            if not self.conflict or not self.score_level_resolution_reference.strip():
                raise ValueError(
                    "A resolution requires an actual conflict and a reference"
                )
        if self.revision_before_assessment is True and not self.revision_description:
            raise ValueError("Known revision requires its original provenance")
        return self

    @property
    def conflict(self) -> bool:
        return bool(
            self.original_teacher_level
            and self.original_teacher_level != rubric_level(self.score)
        )

    @property
    def usable(self) -> bool:
        return not self.conflict or bool(self.score_level_resolution_reference)

    @property
    def classification_source(self) -> str:
        if not self.usable:
            return "UNRESOLVED_SCORE_LEVEL_CONFLICT"
        if (
            self.original_source_status == "TEACHER_SCORE_ONLY_LEVEL_NOT_PROVIDED"
            or self.conflict
        ):
            return "TEACHER_SCORE_RUBRIC_DERIVED"
        return "DOCUMENTED_TEACHER_LEVEL"

    def report(self) -> dict:
        return {
            **self.model_dump(mode="json"),
            "rubric_level": rubric_level(self.score),
            "target_level": rubric_level(self.score) if self.usable else None,
            "classification_source": self.classification_source,
            "score_level_conflict_in_source": self.conflict,
            "usable": self.usable,
        }

    def label_for(
        self, session: dict, start: datetime, end: datetime, purpose: Purpose
    ) -> IndependentLabel:
        if purpose not in ("prospective", "retrospective"):
            raise ValueError("Declare prospective or retrospective analysis explicitly")
        if session["student_code"] != self.student_code:
            raise ValueError("Independent assessment belongs to another learner")
        if not self.usable:
            raise ValueError(
                "Independent assessment has an unresolved score/level conflict"
            )
        category = timing_category(start, end, self.assessed_on, self.timezone)
        if purpose == "prospective" and category != BEFORE:
            raise ValueError(
                f"Not demonstrably before independent assessment: {category}"
            )
        reference = (
            f"Independent teacher CSV SHA256={self.source_csv_sha256}; "
            f"learner={self.student_code}; CSV rows={self.source_row_numbers}; "
            f"classification_source={self.classification_source}; "
            f"original_source_status={self.original_source_status}; "
            f"timing={category}; analysis_purpose={purpose}; {DATE_CONFIRMATION}"
        )
        if self.score_level_resolution_reference:
            reference += " Resolution: " + self.score_level_resolution_reference
        return IndependentLabel(
            student_code=self.student_code,
            session_id=session["game_session_id"],
            concept=session["concept_id"],
            assessment_phase=session["assessment_phase"],
            value=rubric_level(self.score),
            source="teacher",
            source_reference=reference,
            assessed_on=self.assessed_on,
            assessed_at=None,
            assessment_timing={
                BEFORE: "after_gameplay",
                SAME_DAY: None,
                AFTER: "before_gameplay",
            }[category],
            revision_before_assessment=self.revision_before_assessment,
            revision_description=self.revision_description,
            assessment_score=self.score,
            assessment_max_score=10,
            rubric_version=RUBRIC,
            gameplay_independent=True,
        )
