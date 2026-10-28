# Game-Based Learning Analytics

This component lets a learner play linear-equation games, saves their play in
the shared Supabase database, and shows an ML estimate of their mathematical
proficiency. The saved Game result is then used by the AI Tutor. Open
**Equation Game** in the shared application.

Updated: 27 October 2026. [Project README](README.md)

## The games

**Drag & Drop** lets the learner apply operations to an equation, with tap
controls as an alternative to dragging. **Hangman** asks for the value of `x`
through an on-screen number keypad. Both give hints, wrong-answer feedback,
progress and a completion summary. **Mystery Reveal** is shown on the selection
screen as coming next; it is not playable yet.

Each session has **six tasks: 2 Easy, 2 Medium and 2 Hard**. Sinhala is the
default language; the language button switches the current screen without
restarting it. Layouts support desktop and phone widths.

## How a session works

1. **Select the learner.** Choose the learner code (for example `STU_001`),
   the same one used for the Quiz.
2. **Play.** Choose Drag & Drop or Hangman and complete the six tasks.
3. **Saved to Supabase.** While the learner plays, the app sends the session,
   each gameplay event (answers, hints, retries) and each task summary to the
   backend, which stores them in Supabase. If the connection drops, the writes
   wait in a queue and can be recovered. The screen shows **Saved** only once
   the backend confirms everything.
4. **Results.** On completion, the backend calculates the Game result
   (success rate, attempts, wrong answers, retries, hints, skipped steps and
   time) and saves it in Supabase.
5. **ML prediction.** As soon as the session shows **Saved**, the result page
   asks for the prediction automatically; there is nothing to type. It shows
   **Beginner, Intermediate or Advanced** with the probability of each.
6. **Continue to AI Tutor.** The Tutor reads the saved Game and Quiz results
   from Supabase. Both must belong to the same learner and learning cycle;
   they can be completed in either order.

### Where the data is stored

| Supabase table | What it holds |
| --- | --- |
| `game_sessions` | One row per session: learner code, concept, learning cycle, phase, status. |
| `gameplay_events` | Every action during play: answers, hints, retries, timings. |
| `game_task_attempts` | One summary per task. |
| `game_results` | The calculated result for the completed session. |

Learner codes link records across Quiz, Game and Tutor; they are not logins.

### How the prediction is made

- The backend reads the learner's **saved** session from Supabase. It only
  reads; nothing is changed, and the prediction itself is not stored.
- It checks that the saved evidence is complete and consistent, then
  calculates nine inputs: `first_attempt_accuracy`, `game_success_rate`,
  `wrong_attempt_count`, `retry_count`, `total_hint_count`,
  `skipped_step_count`, `game_active_time_sec`, `game_hint_rate` and
  `game_avg_attempts_per_task`.
- A separate worker runs the trained Logistic Regression model (trained in
  Colab on 200 learners, 30 real and 170 simulated; 60% accuracy on 40 test
  records). It checks the model file's checksum before every run.
- Only the browser that finished the session can get its prediction: the
  backend gives it a one-time pass that works for that session, once, for five
  minutes. Refreshing the page or restarting the backend loses the pass.
- If a prediction cannot be made, the card says **Prediction unavailable**.
  The Game result is still saved.

## Running it

### With Docker

From the project root, with `.env` containing the shared Supabase
`DATABASE_URL`:

```bash
docker compose up --build
```

Open **http://localhost:5173** (not `127.0.0.1`) and choose **Equation Game**.
The ML prediction works with no extra setup: Docker builds the model worker
and uses the model file committed in `local_ml_artifacts/`.

### Without Docker

Start the backend from `backend/` and Vite from `frontend/`:

```bash
python -m uvicorn app.main:app --reload --port 8000
npm run dev
```

For the prediction to work natively, `.env` also needs
`GAME_ML_EXPERIMENTAL_ENABLED=true`, `GAME_ML_MODEL_ARCHIVE` (full path to
`local_ml_artifacts/game_ml_model_export_with_fixtures.zip`) and
`GAME_ML_PYTHON` (full path to a separate Python **3.13.12** with
scikit-learn 1.6.1, NumPy 2.1.3, pandas 2.2.3, SciPy 1.16.3 and joblib 1.6.0;
see `backend/app/modules/game/research_inference/worker-requirements.txt`).

### Settings

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL` | Shared Supabase database (in `.env`, never committed). |
| `GAME_ML_EXPERIMENTAL_ENABLED` | Turns the ML prediction on. Docker: on by default. Native: off unless set to `true`. |
| `GAME_ML_TIMEOUT_SEC` | Seconds to wait for the model; default 30, maximum 60. |

## API used by the game

All paths start with `/api/v1/game`.

| Method | Path | Use |
| --- | --- | --- |
| POST | `/sessions` | Create or recover a session. |
| POST | `/events` | Save a gameplay event. |
| POST | `/task-attempts` | Save a task summary. |
| POST | `/sessions/{game_session_id}/complete` | Calculate and save the result; returns the one-time prediction pass. |
| GET | `/results/{game_session_id}` | Read the saved result. |
| POST | `/sessions/{game_session_id}/research-verification` | Get the ML prediction using the one-time pass. |

## Code

| Location | Responsibility |
| --- | --- |
| [frontend/src/game/](frontend/src/game/) | Phaser games, save queue and result page. |
| [backend/app/modules/game/](backend/app/modules/game/) | Saving to Supabase and result calculation. |
| [research_inference/](backend/app/modules/game/research_inference/) | Reading saved sessions, building the nine inputs and running the model. |

Remaining work: Mystery Reveal, Game-specific sign support and further model
evaluation with more real learners.
