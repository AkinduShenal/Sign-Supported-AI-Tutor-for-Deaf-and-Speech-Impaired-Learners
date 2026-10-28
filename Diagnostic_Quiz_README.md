# Diagnostic Quiz

This component gives a learner a ten-question linear-equation quiz, saves their
answers in the shared Supabase database, and shows an ML estimate of which
misconceptions they may have. The saved Quiz result is then used by the Game
and the AI Tutor. Open **Quiz Assessment** in the shared application.

Updated: 28 October 2026. [Project README](README.md)

## The quiz

Each quiz has **ten questions: 4 Easy, 4 Medium and 2 Hard**. For every
question the learner picks an answer and says how confident they are (low,
medium or high). English, Sinhala and bilingual views are available, with a
BODMAS reference, progress indicators and visual answer feedback.

A question allows up to three tries, but only the **first answer** counts. It
is the one that is scored and saved; later tries are practice.

The questions come from a bank of **60 teacher-approved questions**: ten slots
with six variants each. Every new quiz picks one variant per slot at random,
so two learners (or the same learner on a second attempt) usually get
different questions of the same kind and difficulty.

## How a session works

1. **Select the learner.** Enter the learner code (for example `STU_001`),
   the same one used for the Game.
2. **Questions are chosen.** The backend picks the ten questions and saves the
   plan in Supabase. Reloading the page brings back the same questions.
3. **Answer.** Each first answer is sent to the backend with its confidence
   level and response time, and stored in Supabase. If the connection drops,
   answers wait in a queue that survives a refresh and can be recovered.
4. **Results.** After the tenth answer, the backend marks the quiz complete,
   calculates the result (score, mastery level, weakest area, confidence
   insight) and saves it in Supabase.
5. **ML prediction.** The result page then asks for the prediction
   automatically. It shows a probability for each of the four misconception
   categories:

   | Category | Meaning |
   | --- | --- |
   | M1 | Inverse operations |
   | M2 | Balancing both sides |
   | M3 | Negative signs |
   | M4 | Coefficients and division |

   A category is **flagged** when its probability is 0.50 or higher. The four
   probabilities are independent and need not add up to 100%.
6. **Continue to Game or AI Tutor.** The Tutor reads the saved Quiz and Game
   results from Supabase. Both must belong to the same learner and learning
   cycle.

### Where the data is stored

| Supabase table | What it holds |
| --- | --- |
| `quiz_sessions` | One row per quiz: learner code, concept, learning cycle, bank, status. |
| `quiz_session_questions` | The ten questions chosen for that quiz, in order. |
| `quiz_responses` | Each first answer: chosen option, correct or not, confidence, time. |
| `quiz_results` | The calculated result for the completed quiz. |

The questions themselves are in `quiz_questions` and `quiz_question_options`.
Learner codes link records across Quiz, Game and Tutor; they are not logins.

### How the prediction is made

- The backend reads the learner's **saved** answers from Supabase. It only
  reads; nothing is changed, and the prediction itself is not stored.
- From those ten answers it calculates **62 inputs**: correctness, confidence,
  response times and how often each kind of wrong option was chosen.
- A trained multi-label model (four classifiers, one per category) turns the
  inputs into the four probabilities. The model file's checksum is checked
  against its manifest before it is loaded.
- The model was trained on **synthetic data**. The M1–M4 categories were
  verified by the subject teacher on **15 October 2026**; the model's
  predictions themselves have not been validated against real learners.
- If a prediction cannot be made, the card says **Prediction unavailable**
  with a reason and a retry button. The Quiz result is still saved.

## Running it

### With Docker

From the project root, with `.env` containing the shared Supabase
`DATABASE_URL`:

```bash
docker compose up --build
```

Open **http://localhost:5173** and choose **Quiz Assessment**. Docker uses
the 60-question bank and shows the ML prediction with no extra setup; the
model file is committed in `local_ml_artifacts/quiz_dynamic_62_demo/`.

### Without Docker

Start the backend from `backend/` and Vite from `frontend/`:

```bash
python -m uvicorn app.main:app --reload --port 8000
npm run dev
```

Outside Docker the app uses the original **fixed** ten-question quiz, which
has no ML prediction. For the 60-question bank and prediction, set
`QUIZ_ML_ENABLED=true` in `backend/.env` and `VITE_QUIZ_BANK_MODE=dynamic` in
`frontend/.env.local`, then restart both.

### Settings

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL` | Shared Supabase database (in `.env`, never committed). |
| `QUIZ_ML_ENABLED` | Turns the ML prediction on. Docker: on by default. Native: off unless set to `true`. |
| `VITE_QUIZ_BANK_MODE` | `dynamic` (60-question bank) or `fixed` (original ten). Docker: `dynamic`. Native: `fixed`. |

## API used by the quiz

All paths start with `/api/v1/quiz`.

| Method | Path | Use |
| --- | --- | --- |
| POST | `/sessions` | Create or recover a quiz and choose its questions. |
| GET | `/sessions/{quiz_session_id}/questions` | Read the quiz's chosen questions. |
| POST | `/sessions/{quiz_session_id}/responses` | Save a first answer. |
| POST | `/sessions/{quiz_session_id}/complete` | Mark the quiz complete. |
| POST | `/sessions/{quiz_session_id}/analyze` | Calculate and save the result. |
| GET | `/sessions/{quiz_session_id}/result` | Read the saved result. |
| GET | `/sessions/{quiz_session_id}/experimental-prediction` | Get the M1–M4 ML prediction. |

## Code

| Location | Responsibility |
| --- | --- |
| [frontend/src/quiz/](frontend/src/quiz/) | Quiz screens, answer queue, result page and prediction card. |
| [backend/app/modules/quiz/](backend/app/modules/quiz/) | Saving to Supabase, question selection and result calculation. |
| [dynamic_ml_features.py](backend/app/modules/quiz/dynamic_ml_features.py) | Building the 62 inputs from saved answers. |
| [dynamic_ml_inference.py](backend/app/modules/quiz/dynamic_ml_inference.py) | Checking and running the model. |

Remaining work: retrain and evaluate the model with real learners' answers,
review the Sinhala wording, and connect the post-Tutor quiz and Remedial
handoff.
