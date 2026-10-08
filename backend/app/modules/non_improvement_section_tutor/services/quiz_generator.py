import random
from typing import List, Union
from app.modules.non_improvement_section_tutor.models.schemas import EquationCategory, GeneratedQuestion

def generate_single_equation(category: EquationCategory):
    if category == EquationCategory.SINGLE_VARIABLE:
        a = random.randint(1, 10)
        b = random.randint(11, 20)
        question = f"x + {a} = {b}"
        correct_answer = str(b - a)
        
    elif category == EquationCategory.TWO_STEP:
        a = random.randint(2, 5)
        b = random.randint(1, 10)
        x = random.randint(1, 5)
        c = a * x + b
        question = f"{a}x + {b} = {c}"
        correct_answer = str(x)
        
    elif category == EquationCategory.NEGATIVE_NUMBERS:
        x = random.randint(-10, -1)
        a = random.randint(1, 10)
        op = random.choice(['+', '-'])
        if op == '+':
            b = x + a
            question = f"x + {a} = {b}"
        else:
            b = x - a
            question = f"x - {a} = {b}"
        correct_answer = str(x)
        
    elif category == EquationCategory.FRACTIONS_BASIC:
        a = random.randint(2, 5)
        b = random.randint(1, 10)
        question = f"x/{a} = {b}"
        correct_answer = str(a * b)
        
    elif category == EquationCategory.VARIABLES_BOTH_SIDES:
        a = random.randint(3, 6)
        b = random.randint(1, 5)
        c = random.randint(1, 2)
        x = random.randint(1, 4)
        d = (a - c) * x + b
        question = f"{a}x + {b} = {c}x + {d}"
        correct_answer = str(x)
        
    elif category == EquationCategory.DISTRIBUTIVE:
        a = random.randint(2, 5)
        b = random.randint(1, 5)
        x = random.randint(1, 5)
        c = a * (x + b)
        question = f"{a}(x + {b}) = {c}"
        correct_answer = str(x)
        
    else:
        question = "x + 2 = 5"
        correct_answer = "3"
        category = EquationCategory.SINGLE_VARIABLE

    return question, correct_answer, category

def generate_quiz(category_or_categories: Union[EquationCategory, List[EquationCategory]], count: int = 5, start_index: int = 1) -> List[GeneratedQuestion]:

    if isinstance(category_or_categories, list):
        categories = category_or_categories
    else:
        categories = [category_or_categories]

    if not categories:
        categories = [EquationCategory.SINGLE_VARIABLE]

    questions = []
    for i in range(count):
        cat = categories[i % len(categories)]
        q_text, ans_text, final_cat = generate_single_equation(cat)
        
        q_id = f"q{start_index + i}"
        
        questions.append(GeneratedQuestion(
            question_id=q_id,
            question=q_text,
            correct_answer=ans_text,
            category=final_cat
        ))
    return questions
