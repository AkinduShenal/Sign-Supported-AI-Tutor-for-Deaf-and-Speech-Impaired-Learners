# Game ML Milestone 1: offline next-task hint prediction

The research-aligned primary difficulty/mastery comparison is documented in
[`RESEARCH_README.md`](RESEARCH_README.md). This page retains the auxiliary hint
experiment's contract and instructions. Completed work records are
[`ML_Milestone_1.md`](ML_Milestone_1.md) and
[`ML_Milestone_1_1.md`](ML_Milestone_1_1.md).

Member 3 / Accessible Game-Based Learning Analytics. PP1: October 22, 2026.
Implementation date: October 12, 2026. **Offline development foundation only.**
No real learner model has been trained or validated. This package has no API
routes, ORM/configuration imports, database connections, migrations, or gameplay
changes. Existing `game-heuristic-v1` results are independent and unchanged.
Hint use is a behavioural outcome, not a diagnosis of mathematical ability.

## Files and architecture

| File | Responsibility |
| --- | --- |
| `__init__.py` | Isolated offline package marker; no startup hooks |
| `schema.py` | Strict Pydantic task contract, versions, identity/order validation |
| `task_dataset.schema.json` | Generated JSON Schema for task records |
| `dataset.py` | Pure allowlisted features, availability explanations, aligned labels |
| `training.py` | Train-only preprocessing, learner split, Logistic Regression, baseline, metrics |
| `artifacts.py` | Fresh-directory artifact writes, metadata, explicit trusted local loading |
| `inference.py` | Offline probability and binary output using the same feature extraction |
| `__main__.py` | Local JSON export training CLI with diagnostic failures |
| `requirements-ml.txt` | Optional pinned dependencies, separate from shared API requirements |
| `../../../../tests/test_game_ml.py` | Clearly labeled synthetic unit/pipeline fixtures |

The Game package previously had no conflicting learned-model structure. Existing
backend conventions use Pydantic schemas, component-local modules and pytest under
`backend/tests`. This follows those conventions without coupling ML to the live API.

## Dataset contract: `game-task-dataset-v1`

Input is a UTF-8 JSON array of task records. One row represents **one task
occurrence**, aggregating its steps and retries. It is not a step or attempt row.
All fields below are required, including nullable fields, except the derived
label (defaults to null) and the three explicitly marked extra fields. Use JSON
`null` for unavailable measurements, never a fabricated zero. Unknown extra
fields, stringified numbers, boolean counts, nonfinite/negative measurements,
zero denominators and inconsistent counts are rejected.

| Field | Type and meaning |
| --- | --- |
| `student_code` | Nonempty stable pseudonymous learner code; grouping/audit only |
| `session_id` | Nonempty session identity; globally belongs to one learner and learning cycle |
| `learning_cycle_id` | Nonempty cycle identity; audit only |
| `game_type` | Nonempty mode name or null; must be consistent within a session |
| `task_id` | Stable nonempty occurrence identity, unique within session; aggregate retries first |
| `task_order` | Positive integer presentation position, unique within session, supplied by an audited manifest/sequence |
| `difficulty` | `easy`, `medium`, `hard`, or null |
| `concept` | Nonempty concept code or null |
| `total_steps` | Positive integer planned step count, or null |
| `first_attempt_correct_steps` | Nonnegative integer steps correct on their first submitted answer, or null; <= total steps |
| `wrong_attempts` | Nonnegative incorrect answer submissions across the task, or null |
| `retry_count` | Nonnegative answer submissions after the first on each step, summed across steps, or null; not task restarts or transport retries |
| `hint_requests` | Nonnegative count of learner hint requests, including repeated requests, or null |
| `steps_with_hints` | Nonnegative number of distinct planned steps with >=1 hint request, or null; <= total steps and hint requests |
| `task_duration_seconds` | Finite nonnegative audited elapsed time from first task presentation to task closure, or null |
| `task_completed` | True only when all required steps are completed; false for closed incomplete task, null if unknown |
| `next_task_hint_used_label` | Derived 0/1/null; optional on input, nonnull supplied values must match derivation |
| `hint_observation_complete` | **Extra**, boolean default false: audited complete hint observation across this task, needed to trust a zero count |
| `task_duration_reliable` | **Extra**, boolean default false: duration boundaries/clock and no resets verified; otherwise duration is masked |
| `next_task_difficulty` | **Extra**, optional difficulty default null: schedule value captured at the current task's prediction cutoff |

The extra fields gate unreliable historical measurements and prevent future
difficulty leakage. No extra identifiers or heuristic outputs are predictors.
Exporters must supply only audited metrics; set any unreconstructable counter to
null. The validators check structure and consistency, not the truth of collection.

**Ordering:** input array and SQL insertion order are irrelevant. Records are
sorted by `(session_id, task_order)`. Duplicate positions, duplicate task IDs and
inconsistent session owners/cycles/modes fail. Repeated content needs a distinct
occurrence ID. Gaps are allowed: orders 2 and 5 mean task 5 is the *next observed*
task after task 2. This cannot establish behaviour for missing tasks 3/4. An export
must include started but unfinished task rows with known identity/order; dropping
them would silently change the target. Timestamps and lexical task IDs are never
used to infer order. If there is no trustworthy order, dataset preparation is
blocked; this milestone intentionally supplies no speculative database exporter.

## Prediction cutoff, features and labels

Prediction happens after task t is closed (completed or explicitly ended), before
task t+1 starts. All input metrics must be frozen at this cutoff. Later corrections
or events cannot be used retroactively as predictors.

`game-next-hint-features-v1` uses these numeric features:

- `first_attempt_accuracy = first_attempt_correct_steps / total_steps`.
- `wrong_attempts_per_step = wrong_attempts / total_steps` (may exceed 1).
- `retry_count` and `hint_requests` from the current task.
- `share_steps_with_hints = steps_with_hints / total_steps`.
- `task_completed` as 0/1, or missing.
- `task_duration_seconds` only when `task_duration_reliable` is true.

Categorical features are current `game_type`, `concept`, `difficulty`,
`previous_task_difficulty` from the preceding observed task within this session,
and `next_task_difficulty` from the pre-prediction schedule field on the current
row. Current difficulty is the previous task's difficulty relative to the task
being predicted; the separate historical feature describes t-1. The extractor
accepts no future task record and never copies the actual next row's difficulty.

Unavailable raw values stay null, with reasons in `FeatureExtraction.unavailable`.
The first task has no historical difficulty. Duration includes elapsed visual
interaction/support time under the stated definition; it does not imply ability
and must not be called active time without separately validated pause tracking.

No student/session/cycle/task ID, task order, future count/outcome, supplied label,
heuristic mastery, engagement or hint-dependency output enters the feature frame.

For each task t, the target is derived from the next observed row by explicit order
in the **same learner session**:

| Next task evidence | Label / training policy |
| --- | --- |
| Completed, observed hint_requests > 0 | 1; complete hint coverage is unnecessary to establish at least one observed hint |
| Completed, hint_requests = 0, hint_observation_complete = true | 0 |
| Unfinished or completion unknown, even if a hint was seen | Unknown; excluded under the unfinished-target policy |
| Hint count unavailable or zero with incomplete/unverified hint coverage | Unknown; excluded |
| No next row (final task) | Unknown; excluded |

The code never skips an incomplete next row to find a later completed one, crosses
session boundaries, imputes a target, or turns a final task into a negative.
`build_examples()` returns all aligned rows, unknown reasons and next-task audit
identity. `train()` selects only known targets.

## Training and evaluation policy

The default seed is 42 and learner test fraction is 0.25. One fixed
`GroupShuffleSplit` groups by `student_code`, including all sessions/cycles for
each learner together. Both training and test partitions must contain both target
classes. The code does not retry seeds to obtain attractive metrics.

Development guardrails require >=20 valid examples from >=6 learners and both
labels. These are engineering thresholds, **not** a sample-size justification for
research. Too-small, single-class, nonconverged or unsuitable split inputs fail
with clear diagnostics rather than producing an artifact or misleading report.

Numeric preprocessing uses median imputation, missing indicators, and standard
scaling. Completely missing training columns retain their position with sklearn's
zero fallback plus a missing indicator; this is an explicit model preprocessing
choice, not a reconstructed observation. Categorical preprocessing uses an explicit
missing category and one-hot encoding that tolerates unseen held-out categories.
All preprocessing is fitted only on training examples inside the sklearn pipeline.
The classifier is Logistic Regression (`lbfgs`, max_iter=2000). The comparison is
`DummyClassifier(strategy="most_frequent")`, fitted on the same training labels.

Reports include dataset learners/sessions/task rows, valid examples and learners,
class counts, exclusion reasons, missing feature counts, seed, group fraction,
partition learners/sessions/rows/class counts and reproducible canonical example
indices. Both classifiers report confusion matrices (rows actual, columns
predicted; label order [0,1]), per-class precision/recall/F1/support, macro F1 and
balanced accuracy. Undefined precision/recall uses zero with support retained.
The standalone evaluator returns null balanced accuracy for single-class truth;
training rejects such test partitions altogether.

The artifact is the model fitted on the training partition used for the report;
there is no subsequent full-data refit. Real-data validation, statistical power,
confidence intervals, calibration, subgroup/accessibility review, longitudinal
validation and production inference are future work. Probabilities are uncalibrated
estimates of requesting help, never mastery scores or prescriptions to withhold it.

## Run locally

Use the backend's Python 3.13 environment. From the repository root in PowerShell:

```powershell
cd backend
.venv/Scripts/python.exe -m pip install -r app/modules/game/ml/requirements-ml.txt
# If this venv has no pip, the installed system pip can target it instead:
python -m pip --python .venv/Scripts/python.exe install -r app/modules/game/ml/requirements-ml.txt

# This test file imports no app.main, DB settings or ORM modules.
New-Item -ItemType Directory -Path ../tmp -Force | Out-Null
.venv/Scripts/python.exe -m pytest tests/test_game_ml.py -q -p no:cacheprovider --basetemp=../tmp/game-ml-tests
.venv/Scripts/python.exe -m ruff check app/modules/game/ml tests/test_game_ml.py --no-cache
```

On Unix use `.venv/bin/python`. The test fixtures are invented and explicitly
marked `SYNTHETIC`; the CLI/artifact test writes only to pytest temporary paths.
Do not interpret their metrics as learner research findings. No synthetic dataset
is distributed as real collected data, and no trained model is checked into Git.

After collection fixes and an audited, correctly ordered local export exist, the
offline command is:

```powershell
.venv/Scripts/python.exe -m app.modules.game.ml `
  --dataset C:/local-research/audited-task-export.json `
  --output C:/local-research/artifacts/game-hints-run-001 `
  --provenance "Audited export identifier, collection window, exporter version and quality review" `
  --data-kind real_collected
```

This command **was not executed on real data** for Milestone 1. Use
`--data-kind synthetic_development` only for clearly labeled pipeline-validation
fixtures. Keep learner exports/artifacts outside the repository. The CLI emits
the complete metadata report as JSON; it does not connect to a database.

To inspect the machine-readable contract in Python:

```python
from app.modules.game.ml.schema import TaskRecord
schema = TaskRecord.model_json_schema()
```

## Local model artifacts and offline inference

`save_artifact(run, new_directory)` saves fitted preprocessing and classifier
together in `model.joblib`, with `metadata.json` written last. The destination
directory must not exist; no overwrite switch is provided. The directory creation
also prevents a race from overwriting another run. Failed writes leave an
incomplete bundle for inspection; choose a fresh destination after resolving the
cause. Save only the locally produced `TrainingRun`, never arbitrary user objects.

Metadata includes model/dataset/feature versions, actual UTC training timestamp,
explicit source and synthetic/real designation, canonical dataset SHA-256,
input/transformed feature names, target/cutoff definition, library/Python versions,
parameters, split details, evaluation, limitations and model checksum. The bundle
does not store raw learner records or student codes. A checksum detects accidental
changes; it does not authenticate an artifact supplied by someone else.

```python
from app.modules.game.ml.artifacts import load_artifact
from app.modules.game.ml.inference import predict_next_hint
from app.modules.game.ml.schema import TaskRecord

# Only for a bundle produced locally by this code in a trusted directory.
run = load_artifact("C:/local-research/artifacts/game-hints-run-001",
                    trusted_local_artifact=True)
current = TaskRecord.model_validate(current_task_export)
result = predict_next_hint(run, current)  # optional validated previous TaskRecord
```

Loading is disabled by default. **Joblib can execute code when deserializing**:
never enable the trust flag for uploaded/downloaded or other untrusted bundles.
The loader checks schema/model versions, exact runtime versions and checksum
before deserialization. Inference returns probability of label 1, prediction at
threshold 0.5, versions, unavailable feature explanations and offline-development
status. This is a validation helper, not a production endpoint or calibrated model.

See sklearn's official documentation for
[group splitting](https://scikit-learn.org/1.7/modules/generated/sklearn.model_selection.GroupShuffleSplit.html),
[imputation](https://scikit-learn.org/1.7/modules/generated/sklearn.impute.SimpleImputer.html),
and [persistence security and version constraints](https://scikit-learn.org/1.7/model_persistence.html).

## Dependencies on data-collection repairs

The audit used `game/models.py`, `schemas.py`, `service.py`;
`frontend/src/game/analytics/GameSessionTracker.ts`, `types.ts`,
`api/gameApi.ts`, `api/gameBackendSync.ts`, `session/GameSession.ts`,
`phaser/scenes/EquationGameScene.ts`, and `identity.ts`. Relevant limitations in the
current working tree are:

| Dataset requirement | Persisted evidence / remaining dependency |
| --- | --- |
| Stable learner grouping | `GameSession.student_id` is available, but browser localStorage identity can reset or be shared. Reconcile to a stable pseudonymous learner code across devices/cycles before claiming learner-separated validation. |
| Session/cycle/concept | Session has `game_session_id`, `learning_cycle_id`, `concept_id`; no shared cross-module cycle assumption is needed. |
| Explicit task occurrence/order | Attempts contain task/variant IDs and attempt number, **no task_order**. `QUESTION_SHOWN` has a step index, not a task presentation sequence. Need a durable ordered assessment manifest/occurrence sequence; SQL created_at/insert order and task ID sorting are insufficient. |
| Game mode | Present in some event payloads, absent as a session column; older events may lack it. Require consistent audited evidence or null. |
| Difficulty | Nullable `GameTaskAttempt.difficulty_level` and richer event payloads; older rows may lack it. Current selected variant data is not proof of historical content. |
| Planned steps | `step_count` in richer event payloads; no dedicated task column. Historical events/changed local variants cannot be assumed to provide a complete planned denominator. |
| First-attempt correctness | Richer `ANSWER_SUBMITTED` payloads have step index/correctness, but no guaranteed ordered deduplicated event stream. Require first submission identity/order for each planned step; do not count both submitted and correct events or infer accuracy from success/score. |
| Wrong/hint/retry counts | Attempt aggregates and `ANSWER_INCORRECT`/`HINT_REQUESTED`/`RETRY_STARTED` evidence exist. Defaults are not quality guarantees; duplicate attempt ingestion can inflate totals. `RETRY_STARTED` lacks step evidence and means repeated answer selection, not task restart. Define canonical deduplication and count semantics before export. |
| Distinct hinted steps | Richer hint events carry step index; historical ones may not. Need complete, deduplicated step evidence; a hint total alone cannot recover distinct hinted steps. |
| Reliable duration | Tracker `beginStep()` resets at display rebuilds; persisted time is a sum of step times through completion feedback, not an audited first-presentation-to-closure interval. Need reliable task boundaries, clock/reset and pause policy. Keep duration null/unreliable meanwhile. |
| Task completion | Scene emits `TASK_COMPLETED` per **step**. The aggregate attempt is saved on the final step, but historical attempts may be step-level. Need occurrence-level all-step completion evidence; session.status completed does not prove every task completed. |
| Complete hint observation | `GameBackendSync` waits for pending sends on completion but swallows failures and has no durable queue/replay/idempotency guarantee. Absence of hint events is not evidence of no hints. Need audited completeness before zero labels. |
| Known next difficulty | Six variants are selected in memory before play, but an ordered, cutoff-stamped schedule is not persisted. Never read actual next task metadata to manufacture a known plan. |

All independent offline work is implemented without assuming these repairs are
done. Real-data extraction/validation and any production inference remain pending.
No live Supabase connection, database modification, migration, real model training,
commit or push was performed as part of this milestone.

## Milestone 1 verification record (October 12, 2026)

Environment: Python 3.13.12, scikit-learn 1.7.2, NumPy 2.3.3, pandas 2.3.3,
SciPy 1.16.2, joblib 1.5.2. Optional ML dependencies were installed in the local
backend virtual environment; shared API requirements were not edited.

- `pytest tests/test_game_ml.py -q -p no:cacheprovider --basetemp=../tmp/game-ml-verification-1`:
  **55 passed in 7.32s**. The ignored `tmp` parent was created first.
- `pytest tests/test_game_sessions_api.py -q -p no:cacheprovider`:
  **25 passed in 2.49s**, one existing Starlette/httpx deprecation warning.
- Both test commands explicitly set `DATABASE_URL=sqlite+pysqlite:///:memory:`;
  the new ML tests themselves import no database modules.
- Ruff check passed; Ruff formatting check passed for all eight new Python files.
- `git diff --check` passed. Existing unrelated working-tree changes were preserved.

The CLI unit test saved and reloaded temporary local development bundles; other
artifact tests verified overwrite refusal, trust gating, corruption and runtime
version rejection. No real-data CLI run or production model was created.

The **invented deterministic pipeline fixture**, used solely to exercise the
implementation, contains 12 synthetic learner codes, 24 sessions and 144 task
rows. It yields 120 valid examples (60 label 0, 60 label 1) and excludes 24 final
tasks. Seed 42, test fraction 0.25 gives 9 learners / 18 sessions / 90 examples in
training and 3 learners / 6 sessions / 30 examples in test, with zero learner
overlap. Held-out supports are 15 examples per class.

| Synthetic pipeline check | Logistic Regression | Majority baseline |
| --- | --- | --- |
| Confusion matrix, actual rows / predicted columns [0,1] | `[[15,0],[0,15]]` | `[[15,0],[15,0]]` |
| Class 0 precision / recall | 1.0 / 1.0 | 0.5 / 1.0 |
| Class 1 precision / recall | 1.0 / 1.0 | 0.0 / 0.0 |
| Macro F1 | 1.0 | 0.333333 |
| Balanced accuracy | 1.0 | 0.5 |

The perfect fixture score follows the deliberately simple alternating synthetic
pattern. **It provides no evidence of real learner prediction performance.**
Real-data validation and production inference remain incomplete.
