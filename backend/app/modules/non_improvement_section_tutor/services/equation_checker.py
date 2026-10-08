import re
from typing import Tuple, Optional


def normalize_answer(answer: str) -> str:
    answer = answer.strip().lower()
    answer = re.sub(r'\s*=\s*', '=', answer)
    match = re.match(r'([a-z])\s*=\s*(.+)', answer)
    if match:
        variable = match.group(1)
        value = match.group(2).strip()
        try:
            # Try to convert to float for numeric comparison
            num_value = float(value)
            # Convert to int if it's a whole number
            if num_value == int(num_value):
                return f"{variable}={int(num_value)}"
            return f"{variable}={num_value}"
        except ValueError:
            return f"{variable}={value}"
    else:
        try:
            num_value = float(answer)
            if num_value == int(num_value):
                return str(int(num_value))
            return str(num_value)
        except ValueError:
            return answer


def extract_numeric_value(answer: str) -> Optional[float]:
    answer = answer.strip().lower()
    match = re.match(r'[a-z]\s*=\s*(.+)', answer)
    if match:
        try:
            return float(match.group(1).strip())
        except ValueError:
            return None
    try:
        return float(answer)
    except ValueError:
        return None


def identify_error_type(question: str, correct_answer: str, user_answer: str) -> Tuple[str, str]:
    correct_val = extract_numeric_value(correct_answer)
    user_val = extract_numeric_value(user_answer)
    
    if user_val is None:
        return ("invalid_format", "The answer format is not recognized. Expected format like 'x = 4' or just '4'.")
    
    if correct_val is None:
        return ("unknown", "Could not parse the correct answer for comparison.")
    
    # Check for sign error (opposite sign)
    if user_val == -correct_val:
        return ("sign_error", 
                f"Sign error: Got {user_val} but the correct answer is {correct_val}. "
                "Check if you moved terms to the other side correctly — remember to flip the sign.")
    
    # Check for off-by-one or small arithmetic error
    diff = abs(user_val - correct_val)
    if diff <= 2:
        return ("arithmetic_error", 
                f"Small arithmetic mistake: Your answer is off by {diff}. "
                "Double-check your addition or subtraction steps.")
    
    # Check if they forgot to divide
    if correct_val != 0 and user_val != 0:
        if abs(user_val / correct_val) in [2, 3, 4, 5] or (correct_val != 0 and abs(user_val) == abs(correct_val * 2)):
            return ("forgot_division",
                    "It looks like you may have forgotten to divide both sides by the coefficient. "
                    "Remember: if you have something like 2x = 8, divide both sides by 2.")
        
        if correct_val != 0 and abs(correct_val / user_val) in [2, 3, 4, 5]:
            return ("extra_division",
                    "It looks like you divided an extra time or used the wrong divisor.")
    
    if '+' in question and user_val == correct_val + 2 * extract_constant(question):
        return ("operation_confusion",
                "You may have added when you should have subtracted (or vice versa). "
                "When moving a term to the other side of the equation, the operation reverses.")
    
    return ("concept_misunderstanding",
            f"The answer {user_val} is not correct (expected {correct_val}). "
            "Review the steps for solving this type of equation.")


def extract_constant(question: str) -> Optional[float]:
    """Try to extract a constant from a simple equation like 'x + 5 = 12'"""
    match = re.search(r'[+-]\s*(\d+)', question)
    if match:
        return float(match.group(1))
    return 0


def check_answer(question: str, correct_answer: str, user_answer: str) -> dict:
    """
    Check if the student's answer is correct.
    Returns dict with is_correct, error_type, error_description.
    """
    norm_correct = normalize_answer(correct_answer)
    norm_user = normalize_answer(user_answer)
    
    # Direct comparison
    if norm_correct == norm_user:
        return {
            "is_correct": True,
            "error_type": None,
            "error_description": None
        }
    
    # Numeric comparison 
    correct_val = extract_numeric_value(correct_answer)
    user_val = extract_numeric_value(user_answer)
    
    if correct_val is not None and user_val is not None and correct_val == user_val:
        return {
            "is_correct": True,
            "error_type": None,
            "error_description": None
        }
    
    # Answer is wrong — identify the error type
    error_type, error_description = identify_error_type(question, correct_answer, user_answer)
    
    return {
        "is_correct": False,
        "error_type": error_type,
        "error_description": error_description
    }
