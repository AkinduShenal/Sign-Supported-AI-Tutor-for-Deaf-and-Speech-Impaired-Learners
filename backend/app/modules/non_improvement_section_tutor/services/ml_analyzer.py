from typing import List, Dict
from collections import Counter

from app.modules.non_improvement_section_tutor.models.schemas import AnswerResult, WeaknessArea, EquationCategory
from app.modules.non_improvement_section_tutor.services.db import get_user_ml_insights, save_ml_insight, resolve_all_user_ml_insights

def update_insights_on_success(user_id: str, categories: List[EquationCategory]):
    cat_values = [c.value if isinstance(c, EquationCategory) else str(c) for c in categories]
    resolve_all_user_ml_insights(user_id, cat_values)

def analyze_weaknesses(results: List[AnswerResult], user_id: str = None) -> List[WeaknessArea]:
    # Fetch historical ML insight records from PostgreSQL
    existing_insights = get_user_ml_insights(user_id) if user_id else {}

    # Aggregate current submission by category
    category_stats: Dict[str, dict] = {}
    for result in results:
        cat = result.category.value
        if cat not in category_stats:
            category_stats[cat] = {
                "correct": 0,
                "total": 0,
                "error_types": []
            }
        category_stats[cat]["total"] += 1
        if result.is_correct:
            category_stats[cat]["correct"] += 1
        elif result.error_type:
            category_stats[cat]["error_types"].append(result.error_type)
    
    weakness_areas = []
    for cat_value, stats in category_stats.items():
        accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        error_count = stats["total"] - stats["correct"]
        
        # If user got this category 100% correct, clear issue flag in DB
        if error_count == 0:
            if user_id and cat_value in existing_insights:
                prev_attempts = existing_insights[cat_value]["past_attempts"]
                save_ml_insight(user_id, cat_value, prev_attempts, False)
            continue
            
        # Determine severity
        if accuracy < 40:
            severity = "high"
        elif accuracy < 70:
            severity = "medium"
        else:
            severity = "low"
        
        error_counter = Counter(stats["error_types"])
        common_errors = [err for err, _ in error_counter.most_common(3)]
        
        # Look up past ML record
        past_attempts = 0
        if cat_value in existing_insights:
            past_attempts = existing_insights[cat_value]["past_attempts"]
            
        new_attempts = past_attempts + 1
        
        # ML Logic: Flagged as an issue immediately on the first failure
        is_issue = new_attempts >= 1
        
        if user_id:
            save_ml_insight(user_id, cat_value, new_attempts, is_issue)
        
        weakness_areas.append(WeaknessArea(
            category=EquationCategory(cat_value),
            error_count=error_count,
            total_questions=stats["total"],
            accuracy_percentage=round(accuracy, 1),
            common_error_types=common_errors,
            severity=severity,
            is_issue=is_issue
        ))
    
    severity_order = {"high": 0, "medium": 1, "low": 2}
    weakness_areas.sort(key=lambda w: (severity_order[w.severity], w.accuracy_percentage))
    
    return weakness_areas
