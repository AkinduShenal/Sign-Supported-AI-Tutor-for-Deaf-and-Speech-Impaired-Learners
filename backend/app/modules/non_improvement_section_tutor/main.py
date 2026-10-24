from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import sys
import os

# Add parent directory to path for module imports
sys.path.insert(0, os.path.dirname(__file__))

from app.modules.non_improvement_section_tutor.models.schemas import (
    SubmissionRequest, EvaluationResponse, AnswerResult,
    EquationCategory, WeaknessArea, QuizResponse, AdaptiveQuizResponse
)
from app.modules.non_improvement_section_tutor.services.equation_checker import check_answer
from app.modules.non_improvement_section_tutor.services.ml_analyzer import analyze_weaknesses, update_insights_on_success
from app.modules.non_improvement_section_tutor.services.tutorial_generator import generate_tutorials
from app.modules.non_improvement_section_tutor.services.quiz_generator import generate_quiz
from app.modules.non_improvement_section_tutor.services.db import init_db, get_user_ml_insights, has_user_finished, mark_user_finished

# Exportable router for integration into the main backend
router = APIRouter(tags=["Linear Equation Tutor"])


def get_encouragement_message(accuracy: float) -> str:
    """Generate an encouraging message based on accuracy."""
    if accuracy >= 90:
        return "🌟🎉 Amazing work! You're a linear equation superstar! Keep it up! 🎉🌟"
    elif accuracy >= 70:
        return "⭐ Great job! You're doing really well! A little more practice and you'll be perfect! ⭐"
    elif accuracy >= 50:
        return "💪 Good effort! You're getting there! Check out the tutorials below to help you improve! 💪"
    elif accuracy >= 30:
        return "📝 Keep trying! Everyone learns at their own pace. The tutorials below will help you! 📝"
    else:
        return "🌱 Don't give up! Learning takes time. Let's go through the tutorials together step by step! 🌱"


@router.post("/api/evaluate", response_model=EvaluationResponse)
async def evaluate_submission(submission: SubmissionRequest):
    """
    Evaluate a student's submission of linear equation answers.
    
    - Checks each answer for correctness
    - Identifies error types for wrong answers
    - Uses ML to analyze weakness patterns
    - Generates personalized tutorials via DeepSeek AI
    
    Returns detailed results with tutorials for improvement areas.
    """
    if not submission.questions:
        raise HTTPException(status_code=400, detail="No questions provided in submission")
        
    if has_user_finished(submission.user_id):
        return EvaluationResponse(
            user_id=submission.user_id,
            total_questions=len(submission.questions),
            correct_count=len(submission.questions),
            incorrect_count=0,
            overall_accuracy=100.0,
            is_perfect=True,
            results=[],
            focus_area=None,
            tutorial=None,
            next_quiz=None,
            encouragement_message="🌟🎉 You have already completed and mastered this tutor! Great job! 🎉🌟"
        )
    
    # Step 1: Check each answer
    results: List[AnswerResult] = []
    for qa in submission.questions:
        check = check_answer(qa.question, qa.correct_answer, qa.user_answer)
        results.append(AnswerResult(
            question_id=qa.question_id,
            question=qa.question,
            correct_answer=qa.correct_answer,
            user_answer=qa.user_answer,
            is_correct=check["is_correct"],
            category=qa.category,
            error_type=check["error_type"],
            error_description=check["error_description"]
        ))
        
    correct_count = sum(1 for r in results if r.is_correct)
    total = len(results)
    accuracy = (correct_count / total * 100) if total > 0 else 0
    is_perfect = (accuracy == 100)
    
    # Step 2: Fast-path for 100% correct - update DB to mark issue as resolved (False)
    if is_perfect:
        answered_categories = list(set([r.category for r in results]))
        update_insights_on_success(submission.user_id, answered_categories)
        mark_user_finished(submission.user_id)
        
        return EvaluationResponse(
            user_id=submission.user_id,
            total_questions=total,
            correct_count=correct_count,
            incorrect_count=total - correct_count,
            overall_accuracy=round(accuracy, 1),
            is_perfect=True,
            results=results,
            focus_area=None,
            tutorial=None,
            next_quiz=None,
            encouragement_message="🌟🎉 Amazing work! You got everything right! 100% Complete! 🎉🌟"
        )
        
    # Step 3: Analyze weaknesses with ML
    weakness_areas = analyze_weaknesses(results, user_id=submission.user_id)
    
    focus_area = None
    tutorial = None
    next_quiz = None
    
    if weakness_areas:
        # Most severe weakness gets the primary DeepSeek tutorial
        focus_area = weakness_areas[0]
        
        from app.modules.non_improvement_section_tutor.services.tutorial_generator import generate_tutorial_deepseek
        tutorial = await generate_tutorial_deepseek(focus_area)
        
        # Collect ALL categories that had errors in this submission
        wronged_categories = [w.category.value for w in weakness_areas]
        if not wronged_categories:
            wronged_categories = [focus_area.category.value]
            
        # Generate 5 fresh questions with q1, q2, q3... IDs distributed over all wronged categories
        from app.modules.non_improvement_section_tutor.models.schemas import NextQuizPayload
        cat_enums = [EquationCategory(c) for c in wronged_categories]
        questions = generate_quiz(cat_enums, count=5, start_index=1)
        next_quiz = NextQuizPayload(
            targeted_categories=wronged_categories,
            questions=questions
        )
        
    return EvaluationResponse(
        user_id=submission.user_id,
        total_questions=total,
        correct_count=correct_count,
        incorrect_count=total - correct_count,
        overall_accuracy=round(accuracy, 1),
        is_perfect=False,
        results=results,
        focus_area=focus_area,
        tutorial=tutorial,
        next_quiz=next_quiz,
        encouragement_message=get_encouragement_message(accuracy)
    )


@router.get("/api/quiz/{category}", response_model=QuizResponse)
async def get_quiz(category: EquationCategory, count: int = 3):
    """
    Generate a quiz with a specific number of questions for a category.
    """
    questions = generate_quiz(category, count)
    return QuizResponse(category=category, questions=questions)


@router.get("/api/quiz/adaptive/{user_id}", response_model=AdaptiveQuizResponse)
async def get_adaptive_quiz(user_id: str):
    """
    Generate exactly 5 repetitive quiz questions targeting ONLY the user's weak areas 
    from their recorded ML insights.
    """
    insights = get_user_ml_insights(user_id)
    # Find categories with an active issue
    weak_categories = [cat for cat, d in insights.items() if d.get("is_issue")]
    if not weak_categories:
        weak_categories = list(insights.keys())
    if not weak_categories:
        weak_categories = [EquationCategory.SINGLE_VARIABLE.value]
        
    category_enums = [EquationCategory(c) for c in weak_categories]
    questions = generate_quiz(category_enums, count=5, start_index=1)
        
    return AdaptiveQuizResponse(
        user_id=user_id,
        targeted_categories=weak_categories,
        questions=questions
    )


@router.get("/api/focus-area/{user_id}")
async def get_focus_area(user_id: str):
    """
    Get the recommended focus area for a student based on ML insights.
    """
    insights = get_user_ml_insights(user_id)
    issues = [cat for cat, d in insights.items() if d.get("is_issue")]
    focus = issues[0] if issues else (list(insights.keys())[0] if insights else EquationCategory.SINGLE_VARIABLE.value)
    return {
        "user_id": user_id,
        "recommended_focus_area": focus,
        "message": f"📝 Based on your practice history, we recommend focusing on: {focus.replace('_', ' ').title()}"
    }


@router.get("/api/categories")
async def get_categories():
    """
    Get all available equation categories.
    """
    return {
        "categories": [
            {
                "value": cat.value,
                "name": cat.value.replace("_", " ").title(),
                "description": {
                    "single_variable": "Simple equations like x + 5 = 12",
                    "two_step": "Two-step equations like 2x + 3 = 11",
                    "negative_numbers": "Equations with negatives like x - 7 = -3",
                    "fractions_basic": "Equations with fractions like x/2 = 6",
                    "variables_both_sides": "Variables on both sides like 3x + 2 = x + 8",
                    "distributive": "Distributive property like 2(x + 3) = 10",
                }.get(cat.value, "")
            }
            for cat in EquationCategory
        ]
    }


@router.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Linear Equation Tutor API"}


# Standalone FastAPI App
app = FastAPI(
    title="Linear Equation Tutor API",
    description=(
        "API for evaluating basic linear equation answers, "
        "identifying student weaknesses with ML, and generating "
        "personalized tutorials via DeepSeek AI.\n\n"
        "Designed for deaf and speech-impaired 13-year-old learners."
    ),
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def startup_event():
    init_db()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
