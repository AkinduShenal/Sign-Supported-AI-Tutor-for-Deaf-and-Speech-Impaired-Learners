from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class EquationCategory(str, Enum):
    """Categories of basic linear equation skills for 13yo learners"""
    SINGLE_VARIABLE = "single_variable"           # e.g., x + 5 = 12
    TWO_STEP = "two_step"                         # e.g., 2x + 3 = 11
    NEGATIVE_NUMBERS = "negative_numbers"           # e.g., x - 7 = -3
    FRACTIONS_BASIC = "fractions_basic"             # e.g., x/2 = 6
    VARIABLES_BOTH_SIDES = "variables_both_sides"   # e.g., 3x + 2 = x + 8
    DISTRIBUTIVE = "distributive"                   # e.g., 2(x + 3) = 10


class QuestionAnswer(BaseModel):
    """A single question-answer pair submitted by the student"""
    question_id: str = Field(..., description="Unique identifier for the question")
    question: str = Field(..., description="The linear equation question, e.g. 'Solve: 2x + 3 = 11'")
    correct_answer: str = Field(..., description="The correct answer, e.g. 'x = 4'")
    user_answer: str = Field(..., description="The answer given by the student")
    category: EquationCategory = Field(..., description="Category of equation skill being tested")


class SubmissionRequest(BaseModel):
    """Full submission from a student"""
    user_id: str = Field(..., description="Unique student identifier")
    questions: List[QuestionAnswer] = Field(..., description="List of question-answer pairs")


class AnswerResult(BaseModel):
    """Result of evaluating a single answer"""
    question_id: str
    question: str
    correct_answer: str
    user_answer: str
    is_correct: bool
    category: EquationCategory
    error_type: Optional[str] = None  # e.g., "sign_error", "arithmetic_error", "step_skipped", "concept_misunderstanding"
    error_description: Optional[str] = None


class WeaknessArea(BaseModel):
    """An identified area of weakness"""
    category: EquationCategory
    error_count: int
    total_questions: int
    accuracy_percentage: float
    common_error_types: List[str]
    severity: str  # "high", "medium", "low"
    is_issue: bool = False


class GeneratedQuestion(BaseModel):
    question_id: str
    question: str
    correct_answer: str
    category: EquationCategory

class NextQuizPayload(BaseModel):
    targeted_categories: List[str]
    questions: List[GeneratedQuestion]

class EvaluationResponse(BaseModel):
    """Full evaluation response returned to the student"""
    user_id: str
    total_questions: int
    correct_count: int
    incorrect_count: int
    overall_accuracy: float
    is_perfect: bool = False
    results: List[AnswerResult]
    focus_area: Optional[WeaknessArea] = None
    tutorial: Optional[dict] = None
    next_quiz: Optional[NextQuizPayload] = None
    encouragement_message: str

class UserHistory(BaseModel):
    """Stored history for ML analysis"""
    user_id: str
    submissions: List[dict]  # list of past submission results


class QuizResponse(BaseModel):
    category: EquationCategory
    questions: List[GeneratedQuestion]


class AdaptiveQuizResponse(BaseModel):
    """Response containing an adaptive quiz targeting only specific weakness areas"""
    user_id: str
    targeted_categories: List[str]
    questions: List[GeneratedQuestion]
