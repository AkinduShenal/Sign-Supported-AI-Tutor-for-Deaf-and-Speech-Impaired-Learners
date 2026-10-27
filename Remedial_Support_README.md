# Non-Improvement / Remedial Support

Remedial Support evaluates linear-equation answers, identifies the main
weakness and offers a tutorial followed by targeted practice. Open it through
the **Remedial Support** tab in the shared application.

Updated: 27 October 2026. [Project README](README.md)

## Current flow

1. Start an evaluation from the entry screen.
2. The backend checks each submitted answer and groups mistakes by category.
3. It selects the main weakness and returns a short tutorial.
4. The learner works through tutorial slides and five follow-up questions.
5. Answers are evaluated again; further support is returned if needed.

The entry screen currently posts **three fixed demo answers for `student_001`**.
It does not fetch a real post-tutor assessment or the active Quiz/Game learner.
This is a working demonstration of the evaluation/practice loop; automatic
integration with the other components is unfinished.

## Equation categories

| Category ID | Topic | Example |
| --- | --- | --- |
| `single_variable` | One-step addition/subtraction | `x + 5 = 12` |
| `two_step` | Two-step equations | `2x + 3 = 11` |
| `negative_numbers` | Negative values | `x - 7 = -3` |
| `fractions_basic` | Basic fractions | `x/2 = 6` |
| `variables_both_sides` | Variables on both sides | `3x + 2 = x + 8` |
| `distributive` | Brackets/distribution | `2(x + 3) = 10` |

Answer checking normalizes numeric values and simple `x = value` forms. It
compares against the submitted answer key and returns correctness, an error
type and a short description. Current error rules include sign mistakes,
arithmetic differences, missed/extra division and operation confusion.
The endpoint trusts the supplied question/category/answer key; it is not an
independent assessment-authoring or authenticated scoring service.

## Weakness tracking and tutorials

For each category, the backend counts errors, calculates accuracy and keeps
the common error types. Severity is currently **high below 40%**, **medium
below 70%**, otherwise **low** for categories with errors. A failed category
increments its stored attempt count and is flagged as an active issue.
The most severe weakness is selected first.

Although the file is named `ml_analyzer.py`, this implementation uses rules
and stored history, not a separately trained classifier.

When configured, DeepSeek generates the main tutorial. If no key is available
or generation fails, the service returns a built-in tutorial for that category.
The frontend shows an introduction, worked steps, tips and encouragement as
slides, followed by **five fresh questions** distributed across the categories
with errors. It also provides visual question cards, progress, celebrations,
mute/settings controls and an English/Sinhala Google Translate widget.

A perfect submission resolves the submitted categories and records the user
as finished. A later evaluation for a recorded finisher returns the completed
state immediately. This completion flag describes current app behaviour; it
is not a measured pre/post improvement result.

## Running and settings

Prepare dependencies and environment using the
[project setup](README.md#running-the-project). This component requires
**PostgreSQL**; its history service does not support SQLite.

From `backend/`, with the virtual environment activated:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

From `frontend/`:

```bash
npm run dev
```

Open `http://localhost:5173` and choose **Remedial Support**. The main backend
registers this module's router and attempts to initialize its tables on startup.

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection for category history and finishers. |
| `DEEPSEEK_API_KEY` | Optional backend tutorial-generation key. |
| `DEEPSEEK_BASE_URL` | Provider base URL, normally `https://api.deepseek.com/v1`. |
| `VITE_API_BASE_URL` | Frontend API address, normally `http://localhost:8000/api/v1`. |

The Remedial frontend removes `/api/v1` from that API base before calling
`/api/evaluate`. Its routes use `/api`, while the other components use
`/api/v1`. Missing DeepSeek configuration uses fallback tutorials; the database
is still required. Google Translate needs access to its external script.

## API

| Method | Path | Use |
| --- | --- | --- |
| POST | `/api/evaluate` | Evaluate answers, update history and return support. |
| GET | `/api/quiz/{category}` | Generate questions for a category; optional `count`. |
| GET | `/api/quiz/adaptive/{user_id}` | Generate five questions from recorded weak categories. |
| GET | `/api/focus-area/{user_id}` | Read the recommended focus area. |
| GET | `/api/categories` | List all six supported categories. |
| GET | `/api/health` | Check this module's router. |

Example evaluation payload:

```json
{
  "user_id": "demo_remedial_001",
  "questions": [
    {
      "question_id": "q1",
      "question": "2x + 3 = 11",
      "correct_answer": "4",
      "user_answer": "8",
      "category": "two_step"
    }
  ]
}
```

The response includes per-answer `results`, counts, `overall_accuracy`,
`is_perfect`, `focus_area`, `tutorial`, `next_quiz` and
`encouragement_message`. Evaluation writes history/completion records, so use a
disposable development database when trying sample submissions.

## Data and files

The module uses its own PostgreSQL driver/service and two tables:

- `ai_tutor_ml_insights`: user/category key, past attempts, active issue flag
  and update time.
- `ai_tutor_finishers`: user ID and completion time.

These records are separate from Quiz/Game results and Tutor strategy
predictions. The current demo user is not automatically mapped to a shared
`learning_cycle_id`.

| File | Responsibility |
| --- | --- |
| [NonImprovementSectionStartScreen.tsx](frontend/src/components/NonImprovementSectionStartScreen.tsx) | Demo submission and initial loading/error state. |
| [NonImprovementSection.tsx](frontend/src/components/NonImprovementSection.tsx) | Tutorial slides, practice and repeat evaluation. |
| [nonImprovementSectionTutor.ts](frontend/src/api/nonImprovementSectionTutor.ts) | Frontend request helper. |
| [main.py](backend/app/modules/non_improvement_section_tutor/main.py) | Routes and evaluation flow. |
| [models/schemas.py](backend/app/modules/non_improvement_section_tutor/models/schemas.py) | Request/response and category contracts. |
| [services/](backend/app/modules/non_improvement_section_tutor/services/) | Answer checks, history, weakness analysis, tutorials and questions. |

## Checks and remaining work

From `backend/`, the existing health/category/question-generation smoke tests
can run without evaluating against a real database:

```bash
DATABASE_URL=sqlite+pysqlite:///:memory: ./.venv/bin/python -m pytest -q \
  tests/test_linear_tutor_integration.py -k 'not test_linear_tutor_evaluation'
```

The excluded evaluation test calls the PostgreSQL history service. Run it only
against a prepared disposable PostgreSQL database. The SQLite-based combined
regression does not establish that Remedial evaluation works with a deployed
database. There is no dedicated Remedial browser regression script at present.
Shared frontend type/build checks are `npm run build` from `frontend/`.
No new application tests were run for this documentation edit.

Before connecting this to genuine reassessment, replace the demo submission,
link the active learner/cycle, define the pre/post comparison and completion
rules, and add PostgreSQL evaluation/browser coverage. Fraction-answer display,
automatic translation and generated explanations also need content/accessibility
review. The current question UI parses generated answer values as integers,
which limits its handling of non-integer answers.
