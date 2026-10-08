import httpx
import os
import json
from typing import List
from dotenv import load_dotenv

from app.modules.non_improvement_section_tutor.models.schemas import WeaknessArea, EquationCategory

# Load environment variables from the project root .env
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT_ENV_PATH = os.path.join(ROOT_DIR, ".env")
if os.path.exists(ROOT_ENV_PATH):
    load_dotenv(ROOT_ENV_PATH)
else:
    load_dotenv()

def get_deepseek_api_key() -> str:
    return os.getenv("DEEPSEEK_API_KEY")

def get_deepseek_base_url() -> str:
    return os.getenv("DEEPSEEK_BASE_URL")


CATEGORY_DESCRIPTIONS = {
    EquationCategory.SINGLE_VARIABLE: "solving simple equations with one variable (e.g., x + 5 = 12)",
    EquationCategory.TWO_STEP: "solving two-step equations (e.g., 2x + 3 = 11)",
    EquationCategory.NEGATIVE_NUMBERS: "working with negative numbers in equations (e.g., x - 7 = -3)",
    EquationCategory.FRACTIONS_BASIC: "solving equations with basic fractions (e.g., x/2 = 6)",
    EquationCategory.VARIABLES_BOTH_SIDES: "solving equations with variables on both sides (e.g., 3x + 2 = x + 8)",
    EquationCategory.DISTRIBUTIVE: "using the distributive property in equations (e.g., 2(x + 3) = 10)",
}


def build_tutorial_prompt(weakness: WeaknessArea) -> str:
    """
    Build the prompt for DeepSeek to generate a tutorial.
    Tailored for deaf/speech-impaired 13-year-old learners.
    """
    category_desc = CATEGORY_DESCRIPTIONS.get(
        weakness.category, 
        f"solving {weakness.category.value} equations"
    )
    
    error_info = ""
    if weakness.common_error_types:
        error_info = f"\nThe student commonly makes these types of mistakes: {', '.join(weakness.common_error_types)}."
    
    issue_prompt = 'If the weakness is an active issue, use the title "Let us Try a NEW Approach!" and introduce an intuitive physical analogy (like climbing up/down a ladder or balance blocks) with step-by-step visual line breaks.' if getattr(weakness, 'is_issue', False) else ''
    
    prompt = f"""You are a dedicated math tutor creating a step-by-step visual tutorial for a 13-year-old student who is deaf or speech-impaired.

IMPORTANT FORMATTING & ACCESSIBILITY GUIDELINES:
- Use SIMPLE, FRIENDLY, and SHORT sentences.
- Avoid large blocks of text! Every step instruction MUST be short.
- Use literal '\\n' characters inside your JSON strings to force visual line breaks!
- Clear separation between verbal explanation and mathematical equations:
  * Put equations on their OWN line using '\\n' and arrows (→).
  * Do NOT merge equations directly into sentence text.
- EMOJIS: Use friendly emojis like 👉, ➖, ⚖️ as bullet points at the start of each line in the instruction.
- NEVER use terms related to listening, speaking, audio, or voice.
- Show worked examples where each equation transformation is on its own line:
  Example string: "2x + 3 = 11\\n→ 2x + 3 - 3 = 11 - 3\\n→ 2x = 8\\n→ x = 4 ✅"

TOPIC: Create a tutorial on {category_desc}

STUDENT CONTEXT:
- Accuracy in this area: {weakness.accuracy_percentage}%
- Number of errors: {weakness.error_count} out of {weakness.total_questions} questions{error_info}
- Severity level: {weakness.severity}
- Is an active issue: {getattr(weakness, 'is_issue', False)}

{issue_prompt}

Format the response strictly as a JSON object with:
- "title": Short encouraging title
- "introduction": Short 2-sentence welcoming introduction with '\\n' line breaks
- "steps": List of step objects:
    - "step_number": 1, 2, ...
    - "instruction": Clear, short instruction with literal '\\n' separating thoughts
    - "example": Visual math breakdown with each equation step separated by '\\n'
- "practice_problems": List of 3 objects with "problem" and "answer"
- "tips": List of 3 short tips
- "encouragement": Warm closing message

Return ONLY valid JSON, no markdown codeblocks."""
    
    return prompt


async def generate_tutorial_deepseek(weakness: WeaknessArea) -> dict:
    """
    Call DeepSeek API to generate a tutorial for a specific weakness area.
    """
    api_key = get_deepseek_api_key()
    base_url = get_deepseek_base_url()
    if not api_key or api_key == "your_deepseek_api_key_here":
        # Return a fallback tutorial if no API key is configured
        return generate_fallback_tutorial(weakness)
    
    prompt = build_tutorial_prompt(weakness)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful math tutor. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Try to parse the JSON from the response
            # Sometimes the API wraps it in markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            tutorial = json.loads(content)
            tutorial["category"] = weakness.category.value
            tutorial["severity"] = weakness.severity
            return tutorial
            
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        return generate_fallback_tutorial(weakness)


def generate_fallback_tutorial(weakness: WeaknessArea) -> dict:
    """
    Generate a fallback tutorial without the API.
    Used when DeepSeek API key is not configured or API call fails.
    """
    tutorials = {
        EquationCategory.SINGLE_VARIABLE: {
            "title": "⭐ Solving Simple Equations — You Can Do This! ⭐",
            "introduction": "Let's learn how to find the value of x in simple equations!\n🎯 An equation is like a balance — both sides must be equal.",
            "steps": [
                {
                    "step_number": 1,
                    "instruction": "👉 Look at the equation and find what is added or subtracted from x",
                    "example": "x + 5 = 12\n→ Here, 5 is ADDED to x"
                },
                {
                    "step_number": 2,
                    "instruction": "👉 Do the OPPOSITE operation on BOTH sides",
                    "example": "x + 5 - 5 = 12 - 5\n→ Subtract 5 from both sides"
                },
                {
                    "step_number": 3,
                    "instruction": "👉 Simplify to get your answer!",
                    "example": "x = 7 ✅"
                }
            ],
            "practice_problems": [
                {"problem": "x + 3 = 10", "answer": "x = 7"},
                {"problem": "x - 4 = 6", "answer": "x = 10"},
                {"problem": "x + 8 = 15", "answer": "x = 7"}
            ],
            "tips": [
                "💡 Whatever you do to one side, do to the other side too!",
                "💡 Addition and subtraction are opposites",
                "💡 Always check: plug your answer back in to verify"
            ],
            "encouragement": "🌟 You're doing great! Practice makes perfect! Keep going! 🌟"
        },
        EquationCategory.TWO_STEP: {
            "title": "🎯 Two-Step Equations — Step by Step! 🎯",
            "introduction": "Sometimes we need TWO steps to find x. Don't worry — we'll go through it together! 💪",
            "steps": [
                {
                    "step_number": 1,
                    "instruction": "👉 First, remove the number that is added or subtracted (undo + or -)",
                    "example": "2x + 3 = 11  →  Subtract 3 from both sides  →  2x = 8"
                },
                {
                    "step_number": 2,
                    "instruction": "👉 Then, divide both sides by the number in front of x",
                    "example": "2x = 8  →  Divide both sides by 2  →  x = 4"
                },
                {
                    "step_number": 3,
                    "instruction": "👉 Check your answer by putting it back!",
                    "example": "2(4) + 3 = 8 + 3 = 11 ✅"
                }
            ],
            "practice_problems": [
                {"problem": "3x + 2 = 14", "answer": "x = 4"},
                {"problem": "5x - 1 = 24", "answer": "x = 5"},
                {"problem": "4x + 6 = 22", "answer": "x = 4"}
            ],
            "tips": [
                "💡 Remember: Undo addition/subtraction FIRST, then undo multiplication",
                "💡 Think of 'unwrapping' the equation layer by layer",
                "💡 Always check your answer at the end!"
            ],
            "encouragement": "🌟 Two steps? No problem! You've got this! 🌟"
        },
        EquationCategory.NEGATIVE_NUMBERS: {
            "title": "🔢 Negative Numbers in Equations — Don't Be Scared! 🔢",
            "introduction": "Negative numbers might look tricky, but they follow the same rules! Let's learn together! 😊",
            "steps": [
                {
                    "step_number": 1,
                    "instruction": "👉 Remember: negative means 'below zero' on the number line",
                    "example": "... -3, -2, -1, 0, 1, 2, 3 ..."
                },
                {
                    "step_number": 2,
                    "instruction": "👉 When you subtract a negative, it becomes addition!",
                    "example": "x - (-3) = x + 3"
                },
                {
                    "step_number": 3,
                    "instruction": "👉 Solve like normal, but watch the signs carefully",
                    "example": "x - 7 = -3  →  x = -3 + 7  →  x = 4 ✅"
                }
            ],
            "practice_problems": [
                {"problem": "x + 4 = -2", "answer": "x = -6"},
                {"problem": "x - 5 = -8", "answer": "x = -3"},
                {"problem": "x + (-3) = 7", "answer": "x = 10"}
            ],
            "tips": [
                "💡 Draw a number line if you get confused!",
                "💡 Subtracting a negative = Adding (two negatives make a positive)",
                "💡 Always double-check the sign of your answer"
            ],
            "encouragement": "🌟 Negatives are just numbers on the other side of zero! You can handle them! 🌟"
        },
        EquationCategory.FRACTIONS_BASIC: {
            "title": "🍕 Basic Fractions in Equations — Easy as Pie! 🍕",
            "introduction": "Fractions in equations are simpler than they look! We just need to multiply to get rid of them. 🎯",
            "steps": [
                {
                    "step_number": 1,
                    "instruction": "👉 If x is divided by a number, multiply BOTH sides by that number",
                    "example": "x/2 = 6  →  Multiply both sides by 2  →  x = 12"
                },
                {
                    "step_number": 2,
                    "instruction": "👉 If x has a fraction coefficient, multiply by the reciprocal",
                    "example": "(2/3)x = 8  →  Multiply both sides by 3/2  →  x = 12"
                },
                {
                    "step_number": 3,
                    "instruction": "👉 Check by putting your answer back!",
                    "example": "12/2 = 6 ✅"
                }
            ],
            "practice_problems": [
                {"problem": "x/3 = 5", "answer": "x = 15"},
                {"problem": "x/4 = 7", "answer": "x = 28"},
                {"problem": "x/5 = 3", "answer": "x = 15"}
            ],
            "tips": [
                "💡 Division and multiplication are opposites!",
                "💡 Multiply both sides by the denominator to clear the fraction",
                "💡 Always simplify your final answer"
            ],
            "encouragement": "🌟 Fractions are just division in disguise! You've mastered it! 🌟"
        },
        EquationCategory.VARIABLES_BOTH_SIDES: {
            "title": "⚖️ Variables on Both Sides — Balance It Out! ⚖️",
            "introduction": "When x appears on BOTH sides of the equation, we need to move all x's to one side first! 🎯",
            "steps": [
                {
                    "step_number": 1,
                    "instruction": "👉 Move all x terms to ONE side (subtract the smaller x term from both sides)",
                    "example": "3x + 2 = x + 8  →  Subtract x from both sides  →  2x + 2 = 8"
                },
                {
                    "step_number": 2,
                    "instruction": "👉 Now solve like a two-step equation!",
                    "example": "2x + 2 = 8  →  2x = 6  →  x = 3"
                },
                {
                    "step_number": 3,
                    "instruction": "👉 Check: plug x back into BOTH sides!",
                    "example": "Left: 3(3) + 2 = 11  |  Right: 3 + 8 = 11  ✅"
                }
            ],
            "practice_problems": [
                {"problem": "5x + 1 = 3x + 9", "answer": "x = 4"},
                {"problem": "4x - 3 = 2x + 5", "answer": "x = 4"},
                {"problem": "6x + 2 = 4x + 10", "answer": "x = 4"}
            ],
            "tips": [
                "💡 Always move x to the side where it has the BIGGER number",
                "💡 After collecting x terms, it becomes a regular two-step equation",
                "💡 Check your answer in BOTH sides of the original equation"
            ],
            "encouragement": "🌟 Variables on both sides? No match for you! Keep it up! 🌟"
        },
        EquationCategory.DISTRIBUTIVE: {
            "title": "📦 Distributive Property — Unwrap and Solve! 📦",
            "introduction": "When you see parentheses like 2(x + 3), we need to 'distribute' (multiply) first! Let's learn how! 💪",
            "steps": [
                {
                    "step_number": 1,
                    "instruction": "👉 Multiply the outside number by EACH term inside the parentheses",
                    "example": "2(x + 3) = 10  →  2·x + 2·3 = 10  →  2x + 6 = 10"
                },
                {
                    "step_number": 2,
                    "instruction": "👉 Now solve the equation like a two-step problem!",
                    "example": "2x + 6 = 10  →  2x = 4  →  x = 2"
                },
                {
                    "step_number": 3,
                    "instruction": "👉 Check: put x back into the original equation!",
                    "example": "2(2 + 3) = 2(5) = 10 ✅"
                }
            ],
            "practice_problems": [
                {"problem": "3(x + 2) = 15", "answer": "x = 3"},
                {"problem": "4(x - 1) = 12", "answer": "x = 4"},
                {"problem": "2(x + 5) = 16", "answer": "x = 3"}
            ],
            "tips": [
                "💡 Distribute means MULTIPLY the outside number with each inside term",
                "💡 Don't forget to multiply with the sign (+ or -) too!",
                "💡 After distributing, it becomes a normal equation"
            ],
            "encouragement": "🌟 You unwrapped that equation like a pro! Amazing work! 🌟"
        }
    }
    
    tutorial = tutorials.get(weakness.category, {
        "title": "📝 Math Practice Tutorial",
        "introduction": "Let's work on improving your skills in this area!",
        "steps": [{"step_number": 1, "instruction": "Review the basics", "example": "Practice step by step"}],
        "practice_problems": [{"problem": "Review your incorrect answers", "answer": "Try again carefully"}],
        "tips": ["💡 Take your time and work step by step"],
        "encouragement": "🌟 Keep practicing! You're getting better every day! 🌟"
    })
    
    if getattr(weakness, 'is_issue', False):
        tutorial["title"] = "🔄 Let's Try a NEW Approach! 🔄"
        tutorial["introduction"] = "I see this topic is giving you some trouble. Let's look at it in a completely different way and use a new trick!"
        if "tips" in tutorial:
            tutorial["tips"] = [
                "💡 Sometimes trying a new method is all it takes!",
                "💡 Don't worry about past mistakes, we are starting fresh!"
            ] + tutorial["tips"][:1]
    
    tutorial["category"] = weakness.category.value
    tutorial["severity"] = weakness.severity
    return tutorial


async def generate_tutorials(weakness_areas: List[WeaknessArea]) -> List[dict]:
    """
    Generate tutorials for all identified weakness areas.
    Prioritizes high severity areas.
    """
    tutorials = []
    for weakness in weakness_areas:
        tutorial = await generate_tutorial_deepseek(weakness)
        tutorials.append(tutorial)
    return tutorials
