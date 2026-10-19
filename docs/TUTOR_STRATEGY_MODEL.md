# Trained teaching strategy integration — 2026-10-16

The backend now serves the user's Colab `strategy-ml-v1` pipeline. Both
`POST /api/v1/tutor/strategy` and `POST /api/v1/tutor/adaptive-lesson` use it by
default. `RuleBasedStrategyModel` remains available for explicit comparisons.
Model and metadata are bundled under `backend/app/modules/tutor/artifacts/` so
backend-only deployments include them. Install `backend/requirements.txt` and
restart the backend to load this change.

The pipeline predicts the primary strategy. `confidence` is its probability for
that class, not a measured probability of successful tutoring. It was not trained
to select supporting strategies, so `supporting_strategies` is empty. The existing
lesson placement/content heuristics remain separate from the learned strategy.

## Predict using saved Quiz/Game results

`POST /api/v1/tutor/strategy/from-results` reads completed results by session ID:

```json
{
  "student_id": "STU001",
  "concept_id": "linear_equations",
  "quiz_session_id": "QUIZ-001",
  "game_session_id": "GAME-001",
  "learner": {
    "prior_mastery_score": 0.35,
    "preferred_mode": "visual",
    "sign_support_required": true
  }
}
```

Use actual saved IDs and the actual learner profile; these IDs/values are only an
example. The backend reads all ten diagnostic feature values from `quiz_results`
and `game_results`. The eleventh feature, `prior_mastery_score`, must be provided
by the caller because neither result table stores it. It is never inferred from
an arbitrary constant by the serving API.

| Source | Model features |
| --- | --- |
| Quiz result | `quiz_mastery_score`, `quiz_hint_rate`, `misconception_code`, `quiz_difficulty_level`, `recommended_support_level` |
| Game result | `game_mastery_score`, `game_avg_attempts_per_task`, `hint_dependency`, `game_difficulty_level`, `engagement_level` |
| Learner profile | `prior_mastery_score` |

The response includes primary strategy, confidence, `strategy-ml-v1`, and the
prediction/Quiz/Game row IDs. Only `tutor_strategy_predictions` is written.
Repeating the same pair/profile/model version reuses its prediction. An older
rule-based prediction does not prevent a new trained-model prediction.

Missing results return 404. A different student, concept, or conflicting learning
cycle/assessment phase returns 409. Legacy results without cycle identifiers are
accepted only through explicitly selected session IDs for the same student and
concept; missing cycle metadata is not proof that assessments share a cycle.

The original `/strategy` payload format is retained, but it now requires existing
Quiz/Game rows and checks supplied diagnostics against them. It returns 404
instead of inserting missing diagnostics. This removes the previous Tutor-owned
result insertion fallback, including its Game parent-session foreign-key failure.
`/adaptive-lesson` remains a read-only preview of supplied diagnostics; automatic
frontend Quiz/Game handoff is now implemented through the
[automatic Tutor flow](TUTOR_AUTOMATIC_FLOW.md). That flow uses the model author's
confirmed pre-tutor Quiz definition for prior mastery.

## Verification

Supabase was inspected read-only on 2026-10-16. Its result tables contain all ten
required diagnostic columns, with 16 Quiz rows, 26 Game rows and 2 existing Tutor
predictions. No schema changes or dummy rows were needed on Supabase.

There were 17 same-student/concept Quiz/Game combinations. Fifteen conflicted on
cycle/phase and were excluded. The remaining two legacy pairs produced:

| Primary strategy | Model probability |
| --- | --- |
| `step_by_step` | 0.9168131288 |
| `advanced_challenge` | 0.7499515994 |

These two checks explicitly assumed prior mastery `0.5`, with `mixed` presentation
and sign support enabled, because no saved learner profile was available for
those pairs. No predictions using this assumed profile were saved on Supabase.
Both backend predictions and probabilities matched direct inference through the
original Colab pipeline. See the [machine-readable report](verification/tutor-strategy-2026-10-16.json).
This is an integration check, not a fresh accuracy evaluation.

Isolated tests insert synthetic Quiz/Game data with valid Game parent sessions
and foreign-key enforcement. They exercise all five labels through the database
endpoint and verify saved prediction/version/probability, unchanged diagnostics,
missing evidence, mismatched ownership/cycles, model-version cache handling,
idempotency and prediction failure. The direct-model tests independently compare
the supplied artifact with backend inference for each class.

Initial model integration validation: **410 passed, 3 skipped** across the two isolated
commands below. The skips are optional PostgreSQL integrations without configured
disposable local databases. Ruff, dependency checks and `git diff --check` also
passed. Existing Starlette deprecation and Game-training SciPy solver warnings
were reported; there were no test failures.

The exported encoder uses `handle_unknown="ignore"`. The backend's `sign_error`
and `other` misconception categories are absent from its fitted vocabulary, so
they contribute no one-hot category signal. This is preserved from the export,
not remapped to a different misconception. Additional training data is needed
to learn explicit behavior for those categories.

Run tests without the shared database:

```bash
cd backend
DATABASE_URL=sqlite+pysqlite:///:memory: .venv/bin/python -m pytest -q -p no:cacheprovider --ignore=tests/test_tutor_strategy.py
DATABASE_URL=sqlite+pysqlite:///:memory: .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_tutor_strategy.py
```

To repeat only the read-only database comparison, using the configured database:

```bash
cd backend
.venv/bin/python -m scripts.verify_tutor_strategy_model --prior-mastery 0.5 --output ../tmp/tutor-strategy-live-verification.json
```

The CLI clearly marks test-assumed priors. Omit `--prior-mastery` to use only
profiles already saved in matching prediction snapshots and skip other pairs.
