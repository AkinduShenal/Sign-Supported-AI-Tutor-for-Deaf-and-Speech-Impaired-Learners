# ML Milestone 1 — completed work record

Component: Member 3, Game-Based Learning Analytics.
Recorded: October 12, 2026. PP1 deadline: October 22, 2026.

## What was implemented

Milestone 1 established an offline auxiliary experiment predicting whether the
next observed mathematical game task requests at least one hint. It did not
implement the approved primary difficulty/mastery research comparison.

- Strict task-level Pydantic and JSON Schema contracts, version
  `game-task-dataset-v1`, with explicit occurrence identity/order and nulls for
  unavailable metrics.
- Allowlisted accuracy, errors, retries, hints, completion, reliable duration and
  context features. IDs, future outcomes and heuristic outputs are excluded.
- Next-observed-task labels within a learner session. Final tasks, unfinished
  next tasks and unverified zero-hint observations are excluded from supervision.
- Train-only imputation, encoding and scaling; Logistic Regression;
  majority-class baseline; a fixed learner-separated GroupShuffleSplit.
- Binary confusion matrices, precision/recall, macro-F1, balanced accuracy,
  counts, exclusions, split details and provenance metadata.
- Fresh-directory local artifact saving, checksums, explicit trusted loading,
  offline inference and a local JSON training CLI.
- Clearly labelled synthetic unit/pipeline tests and run documentation.

## Source/document files

Created in `backend/app/modules/game/ml/`: `__init__.py`, `schema.py`,
`task_dataset.schema.json`, `dataset.py`, `training.py`, `artifacts.py`,
`inference.py`, `__main__.py`, `requirements-ml.txt`, `README.md`.
Created `backend/tests/test_game_ml.py`.
Added a four-line ML documentation link to `backend/app/modules/game/README.md`.
These changes were uncommitted when this record was created. Optional dependencies
were installed in the existing local backend venv; ignored test artifacts and
bytecode are development outputs, not research data or checked-in models.

## Historical verification

The original implementation run reported **55 ML tests passed in 7.32s** and
**25 Game API tests passed in 2.49s**, with one existing Starlette/httpx warning.
Ruff lint/format and generated-schema checks passed. These are historical results;
new regression results belong in the Milestone 1.1 record.

The invented fixture had 12 learners, 24 sessions, 144 tasks and 120 valid examples
(60 per class); 24 final tasks were excluded. Training/test used 9/3 learners and
90/30 examples. Its deterministic alternating hint pattern produced macro-F1
1.0, versus 0.333333 for the majority baseline. These scores establish no real
learner predictive performance. See [the detailed verification](README.md#milestone-1-verification-record-october-12-2026).

## Research review and preservation decision

The approved primary study compares score-only and score-plus-behaviour models
against independent difficulty/mastery labels, with macro-F1 as the primary
metric. The hint target is auxiliary and is preserved unchanged.

Reusable foundations include task validation, feature calculations, missingness
handling, sklearn preprocessing, grouping and artifact protection. The original
feature lists, target builder, binary evaluator and hint inference are not a
configurable research comparison runner. Milestone 1.1 adds a separate contract
and paired experiment workflow rather than replacing these files.

Real collection still needs stable learner identity, explicit task ordering,
deduplication, reliable first-submission/step counts, timing, completion and hint
coverage. Existing success flags, stars and `game-heuristic-v1` outputs are not
independent ground truth. No real-data model training, production inference,
live Supabase access, migration, commit or push occurred in Milestone 1.

Milestone 1.1 implementation and results will be recorded separately in
`ML_Milestone_1_1.md` when complete.
