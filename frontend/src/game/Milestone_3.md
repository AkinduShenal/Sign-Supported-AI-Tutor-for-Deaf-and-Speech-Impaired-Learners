# Milestone 3 — Persistent Pre-Tutor Assessment Pipeline

## Final Goal

Build one complete working flow:

```text
Linear Equations selected
        ↓
Pre-Tutor Assessment starts
        ↓
2 Easy activities
        ↓
2 Medium activities
        ↓
2 Hard activities
        ↓
Gameplay behaviour captured
        ↓
FastAPI
        ↓
Supabase
        ↓
Feature calculation
        ↓
game_results created
        ↓
Result shown in frontend
        ↓
AI-Tutor-ready output available
```

Do NOT implement final ML in this milestone.

Do NOT implement post-tutor reassessment yet.

Do NOT implement the full curriculum knowledge base yet.

Do NOT rewrite the existing Phaser game.

The existing working game must be extended, not replaced.

---

# STEP 0 — Inspect Before Editing

## Goal

Understand the exact current implementation.

Inspect:

```text
frontend/src/game/
frontend/src/game/scenes/EquationGameScene.ts
frontend/src/game/api/game.ts
frontend/src/game/analytics/
backend/app/modules/game/
backend/app/modules/tutor/
backend/alembic/
backend/app/main.py
```

Also inspect:

- database session configuration;
- API router registration;
- SQLAlchemy Base;
- existing UUID conventions;
- existing Pydantic patterns;
- existing error handling;
- existing tests;
- environment variable handling.

Identify:

1. where the Phaser session starts;
2. where wrong attempts are currently counted;
3. where hints are currently counted;
4. where level completion is handled;
5. where the final summary screen is created;
6. how frontend API requests are normally made;
7. how `GameResult` is currently defined;
8. how Alembic migrations are structured.

### Output before coding

Return:

```text
Current relevant files
Existing reusable code
Files that need modification
Files that need creation
Potential conflicts
```

Then proceed only with Milestone 3.

---

# STEP 1 — Fix and Verify Database Connection

## Goal

FastAPI must successfully connect to the shared Supabase PostgreSQL database.

The current environment may still be pointing to local PostgreSQL.

Check:

```text
DATABASE_URL
```

Do not print secrets.

Confirm whether the backend is connecting to:

```text
Supabase PostgreSQL
```

rather than:

```text
localhost:5432
```

## Verification

Run a safe database connectivity test such as:

```sql
SELECT 1;
```

Then verify the application can open and close a database session successfully.

### Success condition

```text
Backend → Supabase = working
```

Do not continue to gameplay persistence until this works.

---

# STEP 2 — Add Backend Database Models

## Goal

Represent the Game persistence tables in SQLAlchemy.

The required models are:

```text
GameSession
GameplayEvent
GameTaskAttempt
```

Reuse the existing:

```text
GameResult
```

Do NOT create another results table.

---

## GameSession

Support fields equivalent to:

```text
id
game_session_id
student_id
concept_id
learning_cycle_id
assessment_phase
status
started_at
completed_at
created_at
```

Allowed:

```text
assessment_phase:
pre_tutor
post_tutor
```

For this milestone we only actively use:

```text
pre_tutor
```

Status:

```text
in_progress
completed
abandoned
```

---

## GameplayEvent

Fields:

```text
id
game_session_id
task_id
event_type
event_timestamp
event_payload
created_at
```

Initial event types:

```text
GAME_STARTED
QUESTION_SHOWN
ANSWER_SUBMITTED
ANSWER_CORRECT
ANSWER_INCORRECT
HINT_REQUESTED
RETRY_STARTED
TASK_COMPLETED
GAME_COMPLETED
SESSION_ENDED
STEP_SKIPPED
```

---

## GameTaskAttempt

Fields:

```text
id
game_session_id
task_id
attempt_number
attempts_count
wrong_attempts
hints_used
skipped_steps
time_taken_sec
is_completed
is_successful
score
created_at
```

Add these if appropriate for the current design:

```text
activity_id
variant_id
difficulty_level
```

Difficulty:

```text
easy
medium
hard
```

Do not confuse this with learner behavioural difficulty.

---

# STEP 3 — Create an Alembic Migration

## Goal

Make the database structure reproducible.

Create a migration for:

```text
game_sessions
gameplay_events
game_task_attempts
```

Also safely extend `game_results` only if required fields are missing.

Potential fields:

```text
learning_cycle_id
assessment_phase
wrong_attempt_count
retry_count
total_hint_count
skipped_step_count
model_version
```

Do NOT destroy existing data.

Do NOT recreate `game_results`.

Use foreign keys appropriately.

Expected relationships:

```text
game_sessions
    1
    │
    ├──── N gameplay_events
    │
    ├──── N game_task_attempts
    │
    └──── 0..1 game_results
```

## Verification

Run:

```text
alembic upgrade head
```

Verify tables in Supabase.

Run existing backend tests afterwards.

### Success condition

All old tests still pass and the required tables exist.

---

# STEP 4 — Add Pydantic Schemas

## Goal

Define clean request/response validation.

Create schemas for:

### CreateGameSessionRequest

Example fields:

```text
student_id
concept_id
learning_cycle_id
assessment_phase
```

For now:

```text
assessment_phase = pre_tutor
```

---

### CreateGameSessionResponse

Return:

```text
game_session_id
student_id
concept_id
learning_cycle_id
assessment_phase
status
started_at
```

---

### GameplayEventRequest

Fields:

```text
game_session_id
task_id
event_type
event_timestamp
event_payload
```

---

### GameTaskAttemptRequest

Fields:

```text
game_session_id
task_id
activity_id
variant_id
difficulty_level

attempts_count
wrong_attempts
hints_used
skipped_steps
time_taken_sec

is_completed
is_successful
score
```

---

### GameResultResponse

Return the calculated Game Analytics result.

Do not require the frontend to calculate the final rates.

---

# STEP 5 — Implement Game Service Layer

## Goal

Keep database logic and calculations out of FastAPI routes.

Implement service functions approximately equivalent to:

```text
create_game_session()
record_game_event()
save_task_attempt()
complete_game_session()
calculate_session_features()
create_game_result()
get_game_result()
```

Do not put feature calculations inside the Phaser frontend.

---

# STEP 6 — Implement Initial FastAPI Routes

## Goal

Create a minimal usable Game API.

Follow existing project routing conventions.

Functionality equivalent to:

```text
POST /api/v1/game/sessions

POST /api/v1/game/events

POST /api/v1/game/task-attempts

POST /api/v1/game/sessions/{game_session_id}/complete

GET /api/v1/game/results/{game_session_id}
```

Do not add unnecessary endpoints.

---

# STEP 7 — Test Backend Without Phaser

## Goal

Verify persistence independently before connecting the game UI.

Using Swagger/tests:

### 1. Create session

Example:

```json
{
  "student_id": "TEST001",
  "concept_id": "simple_equations",
  "learning_cycle_id": "<uuid>",
  "assessment_phase": "pre_tutor"
}
```

### 2. Add event

```json
{
  "game_session_id": "...",
  "task_id": "TASK_E_001",
  "event_type": "QUESTION_SHOWN",
  "event_payload": {
    "difficulty_level": "easy",
    "variant_id": "LEQ_E_001"
  }
}
```

### 3. Save task attempt

Example:

```text
attempts_count = 3
wrong_attempts = 2
hints_used = 1
time_taken_sec = 38
is_completed = true
is_successful = true
```

### 4. Complete session

Confirm the backend closes the session.

### Success condition

Supabase should show:

```text
1 game_sessions row
multiple gameplay_events rows
game_task_attempts rows
```

Do not connect Phaser until this works.

---

# STEP 8 — Connect Phaser to Create a Game Session

## Goal

When Linear Equations pre-assessment starts:

```text
Phaser
   ↓
POST /game/sessions
```

Save returned:

```text
game_session_id
learning_cycle_id
```

for the current assessment.

Do not generate a new session ID per question.

One assessment:

```text
1 game_session_id
```

All six diagnostic tasks belong to it.

---

# STEP 9 — Send Gameplay Events

## Goal

Replace browser-only tracking with persistent tracking while preserving the existing local UI behaviour.

When assessment starts:

```text
GAME_STARTED
```

When task appears:

```text
QUESTION_SHOWN
```

When learner submits:

```text
ANSWER_SUBMITTED
```

Wrong:

```text
ANSWER_INCORRECT
```

Hint:

```text
HINT_REQUESTED
```

Retry:

```text
RETRY_STARTED
```

Correct:

```text
ANSWER_CORRECT
```

Task done:

```text
TASK_COMPLETED
```

Assessment done:

```text
GAME_COMPLETED
```

Do not block the UI unnecessarily while recording non-critical events.

Handle failed requests safely.

---

# STEP 10 — Build Difficulty Structure

## Goal

Convert the current Linear/Simple Equation game into:

```text
Easy
Medium
Hard
```

For this milestone the assessment blueprint is:

```text
2 Easy
2 Medium
2 Hard
```

Total:

```text
6 diagnostic tasks
```

Use the official Equations lesson as the basis.

Initial concept mapping:

```text
EASY
- basic one-step equations
- simple addition/subtraction
- simple multiplication/division

MEDIUM
- variable on both sides
- bracket equations
- two-step equations

HARD
- fractional equations
- algebraic fractions
- selected equation word-problem structures
```

Do not include simultaneous equations or quadratic equations in Milestone 3.

Scope remains:

```text
Lesson 15.1 Simple Equations
```

---

# STEP 11 — Create Question / Variant Data Structure

## Goal

Stop hard-coding only one equation per level.

For the first prototype create:

```text
6 Easy variants
6 Medium variants
6 Hard variants
```

Total:

```text
18 variants
```

Each variant needs:

```text
variant_id
activity_id
concept_id
difficulty_level
question data
correct answer
hint data
```

Prefer structured configuration.

Example:

```json
{
  "variant_id": "LEQ_E_001",
  "activity_id": "LEQ_ONE_STEP_ADD",
  "concept_id": "simple_equations",
  "difficulty_level": "easy",
  "equation_type": "x_plus_a_equals_b",
  "a": 3,
  "b": 7,
  "answer": 4
}
```

Do not build a database question bank yet unless needed.

A typed local data structure is acceptable for this milestone.

---

# STEP 12 — Implement Question Selection

## Goal

For every assessment:

```text
select 2 Easy
select 2 Medium
select 2 Hard
```

Within each level:

```text
shuffle eligible variants
```

The order of difficulty remains:

```text
Easy
→ Medium
→ Hard
```

But questions inside each tier are randomized.

Example assessment:

```text
E5
E2
M1
M6
H4
H3
```

---

# STEP 13 — Implement the “Maximum Two Uses” Rule

## Goal

A learner should not repeatedly receive the exact same variant forever.

Before choosing variants:

```text
Find prior task attempts for:
student
concept
variant
```

If:

```text
usage_count >= 2
```

exclude the variant.

Selection:

```text
All variants
   ↓
Filter usage_count < 2
   ↓
Shuffle
   ↓
Select
```

If every variant reaches the limit, do not crash.

For Milestone 3:

```text
fallback to least-used variants
```

and document this behaviour.

More sophisticated generated variants can come later.

---

# STEP 14 — Save Task Summaries

## Goal

After each diagnostic task finishes, create/update a `game_task_attempts` record.

Example:

```text
task_id = ASSESS_E_01

activity_id = LEQ_ONE_STEP_ADD

variant_id = LEQ_E_004

difficulty_level = easy

attempts_count = 3

wrong_attempts = 2

hints_used = 1

skipped_steps = 0

time_taken_sec = 34

is_completed = true

is_successful = true
```

This is the bridge between raw events and final session analytics.

---

# STEP 15 — Build Backend Feature Engineering

## Goal

At assessment completion calculate final features from persisted task/session data.

Calculate:

```text
tasks_total

tasks_attempted

tasks_completed

successful_tasks

game_success_rate

game_completion_rate

game_avg_attempts_per_task

game_hint_rate

game_active_time_sec

wrong_attempt_count

retry_count

total_hint_count

skipped_step_count
```

Document each formula.

Example:

```text
game_success_rate
=
successful_tasks / tasks_attempted
```

Handle division by zero.

Example:

```text
game_completion_rate
=
tasks_completed / tasks_total
```

Choose and document one consistent definition for:

```text
game_hint_rate
```

Do not silently change its meaning later.

---

# STEP 16 — Complete Assessment Automatically

## Goal

The backend should determine that the pre-assessment is complete when:

```text
2 Easy diagnostic tasks processed
AND
2 Medium diagnostic tasks processed
AND
2 Hard diagnostic tasks processed
```

Success is NOT required.

A wrong or skipped task can still count as processed diagnostic evidence if it is properly recorded.

The frontend must not simply hard-code:

```text
questionNumber === 6
```

as the only source of truth.

Backend completion must be validated.

---

# STEP 17 — Create `game_results`

## Goal

Once the assessment is complete:

```text
Persisted task behaviour
        ↓
Feature Engineering
        ↓
game_results
```

Save:

```text
student_id

concept_id

game_session_id

learning_cycle_id

assessment_phase = pre_tutor

tasks_total

tasks_attempted

tasks_completed

successful_tasks

game_success_rate

game_completion_rate

game_avg_attempts_per_task

game_hint_rate

game_active_time_sec

wrong_attempt_count

retry_count

total_hint_count

skipped_step_count
```

If learner-level ML fields are not ready yet:

```text
behavioral_difficulty
game_mastery_score
engagement_level
```

must NOT be falsely presented as final ML predictions.

Use the existing schema carefully.

If required, mark prototype values clearly or leave ML-specific fields out of this milestone if schema permits.

---

# STEP 18 — Show Result in Frontend

## Goal

Upgrade the existing summary screen.

Show:

```text
Linear Equations
Pre-Tutor Assessment Complete

Tasks               6
Successful           4
Success Rate         67%
Completion Rate      100%
Average Attempts     1.8
Hint Rate            33%
Wrong Attempts       4
Retries              3
Hints Used           2
Active Time          4m 35s
```

Do not make UI beautification the priority.

The purpose is to prove analytics.

---

# STEP 19 — AI Tutor Ready Output

## Goal

Expose the final Game result through the API.

AI Tutor should be able to retrieve/use at least:

```text
student_id
concept_id
game_session_id

game_success_rate
game_completion_rate
game_avg_attempts_per_task
game_hint_rate
game_difficulty_level

game_active_time_sec

assessment_phase
learning_cycle_id
```

Also expose richer behavioural evidence when useful:

```text
wrong_attempt_count
retry_count
total_hint_count
skipped_step_count
```

Do not implement AI Tutor logic inside the Game component.

---

# STEP 20 — Testing

## Backend tests

Test:

```text
create game session

invalid assessment phase rejected

record event

invalid event type rejected

save task attempt

complete session

rate calculations

division-by-zero protection

game result creation

foreign-key integrity
```

---

## Frontend tests / manual checks

Verify:

```text
game starts normally

questions render correctly

correct answer works

wrong answer works

hint works

retry works

Easy → Medium → Hard order works

questions shuffle

same question does not exceed allowed usage

refresh/error does not corrupt completed DB records

summary appears
```

---

# STEP 21 — Milestone 3 Final Verification

Before marking Milestone 3 complete, demonstrate this exact flow:

```text
1. Select Linear Equations

2. Start assessment

3. Supabase gets game_sessions row

4. Play Easy question

5. Make one wrong answer

6. Request one hint

7. Retry and answer correctly

8. Supabase contains those events

9. Continue through:
   2 Easy
   2 Medium
   2 Hard

10. Assessment completes

11. game_task_attempts contains 6 task summaries

12. Backend calculates session features

13. game_results row is created

14. Frontend shows analytics

15. GET game result returns AI-Tutor-ready JSON
```

---

# Milestone 3 Definition of Done

Only mark Milestone 3 complete when all these are true:

```text
[ ] Backend connects to Supabase

[ ] GameSession model exists

[ ] GameplayEvent model exists

[ ] GameTaskAttempt model exists

[ ] Database migration works

[ ] Game API routes exist

[ ] Phaser creates a backend session

[ ] Gameplay events persist

[ ] Task attempts persist

[ ] Linear Equations assessment uses
    Easy → Medium → Hard

[ ] Assessment uses 2 + 2 + 2 tasks

[ ] Questions shuffle

[ ] Question usage history is considered

[ ] Backend calculates analytics

[ ] game_results is created automatically

[ ] Result is shown in frontend

[ ] AI-Tutor-ready JSON is available

[ ] Existing frontend build passes

[ ] Existing backend tests pass

[ ] New Game tests pass
```

---

# Important Rules

1. Do not rewrite `EquationGameScene.ts` from scratch.

2. Reuse existing Phaser mechanics.

3. Do not break AI Tutor code.

4. Do not modify Quiz code unless integration requires it.

5. Do not implement final ML yet.

6. Do not implement full curriculum ingestion yet.

7. Do not implement post-tutor reassessment yet.

8. Do not introduce Redis, queues or microservices.

9. Do not calculate final analytics only in the frontend.

10. Keep raw gameplay evidence in the database.

11. Keep task summaries separate from raw events.

12. Keep final session analytics in `game_results`.

13. Run build/tests after every major step.

14. Do not proceed after a failing stage until the failure is understood.

15. Report exactly which files changed after every stage.

the work in these five batches:
Batch 1
Steps 0–3
Database connection + models + migration

Batch 2
Steps 4–7
Schemas + service + API + backend verification

Batch 3
Steps 8–14
Phaser connection + event tracking + Easy/Medium/Hard + variants

Batch 4
Steps 15–19
Feature engineering + completion + game_results + frontend result + AI Tutor payload

Batch 5
Steps 20–21
Testing + final end-to-end verification