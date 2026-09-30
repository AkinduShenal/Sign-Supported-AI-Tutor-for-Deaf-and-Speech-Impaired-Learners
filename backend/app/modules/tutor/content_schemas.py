from enum import StrEnum

from pydantic import BaseModel, Field


class SignValidationStatus(StrEnum):
    PENDING = "pending"
    VALIDATED = "validated"


class SignReference(BaseModel):
    sign_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_page: int = Field(gt=0)
    source_entry: int = Field(gt=0)
    animation_asset: str | None = None
    validation_status: SignValidationStatus


class SignSupportedText(BaseModel):
    text: str = Field(min_length=1)
    sign_actions: list[str]


class LessonStep(BaseModel):
    order: int = Field(gt=0)
    instruction: str = Field(min_length=1)
    expression: str = Field(min_length=1)
    sign_actions: list[str]


class WorkedExample(BaseModel):
    problem: str = Field(min_length=1)
    steps: list[LessonStep] = Field(min_length=1)
    answer: str = Field(min_length=1)


class PracticeFeedback(BaseModel):
    correct: str = Field(min_length=1)
    incorrect: str = Field(min_length=1)


class PracticeQuestion(BaseModel):
    question_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    hint: SignSupportedText
    expected_answer: str = Field(min_length=1)
    feedback: PracticeFeedback


class TutorLessonResponse(BaseModel):
    concept_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    learning_objective: str = Field(min_length=1)
    simple_explanation: SignSupportedText
    sign_glossary: list[SignReference] = Field(min_length=1)
    worked_examples: list[WorkedExample] = Field(min_length=1)
    practice_questions: list[PracticeQuestion] = Field(min_length=1)
