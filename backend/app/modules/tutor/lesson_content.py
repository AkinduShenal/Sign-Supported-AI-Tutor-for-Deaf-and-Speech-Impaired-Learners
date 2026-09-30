from app.modules.tutor.content_schemas import (
    LessonStep,
    PracticeFeedback,
    PracticeQuestion,
    SignReference,
    SignSupportedText,
    SignValidationStatus,
    TutorLessonResponse,
    WorkedExample,
)


SIGN_SOURCE_TITLE = "Maths Sign Language"


def _sign(
    sign_id: str,
    label: str,
    source_page: int,
    source_entry: int,
) -> SignReference:
    return SignReference(
        sign_id=sign_id,
        label=label,
        source_title=SIGN_SOURCE_TITLE,
        source_page=source_page,
        source_entry=source_entry,
        animation_asset=None,
        validation_status=SignValidationStatus.PENDING,
    )


LINEAR_EQUATION_BALANCING = TutorLessonResponse(
    concept_id="linear_equation_balancing",
    title="Linear Equation Balancing",
    learning_objective=(
        "Solve a one-step linear equation by applying the same operation to both sides."
    ),
    simple_explanation=SignSupportedText(
        text=(
            "An equation is like a balance. To keep both sides equal, perform "
            "the same operation on both sides."
        ),
        sign_actions=["ALGEBRA", "EQUATION", "BALANCE"],
    ),
    sign_glossary=[
        _sign("ADDITION", "Addition", source_page=1, source_entry=1),
        _sign("SUBTRACTION", "Subtraction", source_page=1, source_entry=2),
        _sign("MULTIPLICATION", "Multiplication", source_page=1, source_entry=3),
        _sign("DIVISION", "Division", source_page=1, source_entry=4),
        _sign("BALANCE", "Balance", source_page=7, source_entry=38),
        _sign("ALGEBRA", "Algebra", source_page=16, source_entry=94),
        _sign("EQUATION", "Equation", source_page=17, source_entry=97),
        _sign("SUBSTITUTION", "Substitution", source_page=17, source_entry=101),
        _sign("NUMBER_3", "Number 3", source_page=2, source_entry=11),
        _sign("NUMBER_4", "Number 4", source_page=2, source_entry=11),
        _sign("NUMBER_7", "Number 7", source_page=2, source_entry=11),
    ],
    worked_examples=[
        WorkedExample(
            problem="x + 3 = 7",
            steps=[
                LessonStep(
                    order=1,
                    instruction=(
                        "Identify the operation next to x. Three is added to x."
                    ),
                    expression="x + 3 = 7",
                    sign_actions=[
                        "ALGEBRA",
                        "ADDITION",
                        "NUMBER_3",
                        "EQUATION",
                        "NUMBER_7",
                    ],
                ),
                LessonStep(
                    order=2,
                    instruction="Subtract 3 from both sides to keep the balance.",
                    expression="x + 3 - 3 = 7 - 3",
                    sign_actions=[
                        "ALGEBRA",
                        "ADDITION",
                        "NUMBER_3",
                        "SUBTRACTION",
                        "NUMBER_3",
                        "EQUATION",
                        "NUMBER_7",
                        "SUBTRACTION",
                        "NUMBER_3",
                    ],
                ),
                LessonStep(
                    order=3,
                    instruction="Simplify both sides.",
                    expression="x = 4",
                    sign_actions=["ALGEBRA", "EQUATION", "NUMBER_4"],
                ),
                LessonStep(
                    order=4,
                    instruction="Substitute 4 for x to check the answer.",
                    expression="4 + 3 = 7",
                    sign_actions=[
                        "SUBSTITUTION",
                        "NUMBER_4",
                        "ADDITION",
                        "NUMBER_3",
                        "EQUATION",
                        "NUMBER_7",
                    ],
                ),
            ],
            answer="x = 4",
        )
    ],
    practice_questions=[
        PracticeQuestion(
            question_id="linear-equation-balancing-01",
            prompt="Solve x + 5 = 12.",
            hint=SignSupportedText(
                text=("Keep x by itself. Subtract 5 from both sides of the equation."),
                sign_actions=["EQUATION", "BALANCE", "SUBTRACTION"],
            ),
            expected_answer="x = 7",
            feedback=PracticeFeedback(
                correct=("Correct! You subtracted 5 from both sides, so x equals 7."),
                incorrect=(
                    "Try again. Keep the equation balanced by subtracting 5 "
                    "from both sides."
                ),
            ),
        )
    ],
)


LESSON_CATALOG: dict[str, TutorLessonResponse] = {
    LINEAR_EQUATION_BALANCING.concept_id: LINEAR_EQUATION_BALANCING,
}


def get_lesson(concept_id: str) -> TutorLessonResponse | None:
    return LESSON_CATALOG.get(concept_id)
