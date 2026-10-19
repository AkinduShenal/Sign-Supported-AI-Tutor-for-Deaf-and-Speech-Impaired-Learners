# Research-aligned comparative ML — Milestone 1.1

Member 3 / Game-Based Learning Analytics. PP1: October 22, 2026.

The primary experiment asks whether gameplay behaviour improves independently
assessed mathematical difficulty or concept-mastery classification on unseen
learners. The original next-task hint experiment remains an auxiliary experiment
with its original CLI, contracts and tests. This implementation is offline only;
it does not change gameplay, UI, database tables, heuristic results or other modules.

## Prediction unit and independent labels

`game-research-observation-v1` has one record per **learner–concept–assessment
session**, uniquely keyed by session, concept and assessment phase. Aggregate
every task occurrence for the concept within the declared observation window,
including unfinished tasks. Repeated task steps/attempts are not independent
training examples. Multiple concepts/sessions for one learner remain in the same
train/test group.

The observation is frozen at `observation_ended_at`. Exporters must ensure no
later gameplay or external assessment outcomes enter the measurements. Label
dates may precede or follow the window: the chosen study protocol must distinguish
diagnostic classification from prospective prediction. This code stores the dates
and excludes all label fields from predictors; it does not establish causal order
or independently verify an assessment's truth.

`difficulty_label` means **learner mathematical difficulty**, not question/variant
Easy/Medium/Hard. `mastery_label` is a separate optional target. Neither is inferred
from the other, generated using gameplay thresholds, or read from Game heuristic
outputs. The researcher must supply the approved rubric and class definitions.

Each embedded label is explicitly linked to the same learner, session, concept
and assessment phase as its gameplay observation. Mismatches are rejected before
cohort preparation. Future assessment scores, label source/rubric/date and label
values are never features. In particular, an assessment score that directly
defines the target must not also be smuggled into the gameplay-score field.

## Input fields

The Pydantic contract is in `research_schema.py`; its generated machine-readable
contract is `research_dataset.schema.json`. Unknown fields, nonfinite numbers,
boolean counts, negative counts, invalid proportions and contradictory totals
are rejected. Required nullable metrics must be supplied as `null` if unavailable.
Structural validation cannot replace auditing the underlying observations.

| Field | Meaning / validation |
| --- | --- |
| `student_code`, `session_id` | Nonempty anonymous learner and game-session identities; grouping/audit only |
| `concept` | Nonempty mathematics concept code |
| `game_type` | Nonempty mode name or null |
| `activity_ids` | Nonempty list of distinct activity identifiers; not automatically predictors |
| `assessment_phase` | `pre_tutor` or `post_tutor` |
| `observation_started_at`, `observation_ended_at` | Timezone-aware ISO timestamps; end strictly after start |
| `total_steps` | Positive planned step denominator, or null |
| `first_attempt_correct_steps` | Nonnegative number correct on first submitted answer, or null; <= total steps |
| `first_attempt_observation_complete` | Default false; first-submission evidence and complete roster verified |
| `score_definition` | Fixed `first_attempt_correctness_v1` |
| `gameplay_score` | Optional normalized score; derived when evidence is verified; a supplied value must match derivation |
| `wrong_attempts`, `retry_count` | Audited whole-window counts or null; retries mean answer submissions after the first per step |
| `hint_count`, `steps_with_hints` | Audited request count and distinct hinted steps, or null; hinted steps <= hints and total steps |
| `hint_observation_complete` | Default false; unverified hint counts/rates are masked in model inputs |
| `tasks_total` | Positive count of every task occurrence in the observation unit |
| `tasks_completed` | Known completed-task count, or null; <= tasks_total |
| `task_completed` | Whole unit/all tasks completed, false for incomplete, or null; must agree with known counts |
| `skipped_steps` | Genuinely observed skipped-step count, or null; <= total steps |
| `task_duration_seconds` | Sum of audited task elapsed durations within the window, or null |
| `task_duration_reliable` | Default false; when true duration must exist and cannot exceed the observation window |
| `difficulty_label` | Required nullable independent label; no next-task shift or final-task exclusion |
| `mastery_label` | Optional nullable independent label |

Each nonnull label contains:

| Label field | Meaning |
| --- | --- |
| `student_code`, `session_id`, `concept`, `assessment_phase` | Must match the observation exactly |
| `value` | Nonempty rubric class, checked against the experiment's explicit class list |
| `source` | `teacher`, `quiz` or `test` |
| `source_reference` | Assessment/reference identifier, not an identifying learner name |
| `assessed_at` | Timezone-aware assessment timestamp |
| `rubric_version` | Nonempty rubric identifier/version |
| `gameplay_independent` | Must be true; explicit quality assertion, not proof of independence |

## Score definition and aggregation

`gameplay_score = sum(first_attempt_correct_steps) / sum(total_planned_steps)`.
The Python property `first_attempt_accuracy` exposes the same measure. It is not
duplicated as another predictor. There is no use of `is_successful`, local stars,
heuristic mastery, or independent assessment outcomes to construct this score.

The denominator includes planned steps in abandoned tasks. Unattempted/skipped
steps earn no first-attempt correctness only when the complete roster and event
coverage are audited; missing evidence does not become zero. Without a known
denominator, numerator or verified coverage, score is unavailable. A supplied score
without that evidence, or one inconsistent with the ratio, is rejected.

`aggregate_observation()` accepts validated original `TaskRecord` rows, explicit
`ObservationContext`, external labels and first-attempt coverage evidence. It:

- Validates unique task identities/orders and matching learner/session/concept/mode.
- Sums denominators and numerators, rather than averaging task percentages.
- Preserves every roster task, including the final and abandoned tasks.
- Returns null for a total if any contributing task's count is unavailable.
- Accepts skipped-step evidence only when it covers the exact task roster.
- Uses duration only when every contributing task is marked reliable.

`TaskRecord` does not have authoritative task timestamps, activity linkage or
first-submission completeness evidence. The context/roster/cutoff must be audited
externally. This helper is not a speculative database exporter and does not repair
the existing collection defects.

## Paired feature sets and cohort

**Model A — `score_only`:** gameplay_score, plus explicitly configured common
context. **Model B — `score_plus_behaviour`:** every Model A feature plus:

- Wrong attempts and wrong attempts per planned step.
- Retries and retries per planned step.
- Verified hint requests and hint usage rate (distinct hinted steps / planned steps).
- Completion rate (completed tasks / roster tasks) and whole-unit completion.
- Observed skipped steps and skipped steps per planned step.
- Reliable task duration and duration per planned step.

Common context defaults to empty. Only `concept`, `game_type` and
`assessment_phase` may be enabled, and the identical context is included in both
models. IDs, timestamps, activity IDs, label data, heuristic outputs and future
task outcomes are not selectable predictor columns.

The runner validates/sorts the complete dataset once. It selects observations
with the chosen independent target and an audited score **once for both models**.
Unknown target labels and unavailable scores are reported as cohort exclusions.
Unconfigured nonnull classes fail rather than silently disappearing. Missing
behaviour does not remove participants from Model B.

These behaviour measures can also be examined as descriptive engagement indicators.
They do not constitute a validated engagement diagnosis. This milestone does not
implement an engagement classifier, accessibility user study, sequence-pattern
model, or inference that slow responses/hint requests imply low ability.

## Configurable training and fair evaluation

`ExperimentConfig` selects target (`difficulty`/`mastery`), explicitly ordered
class names, classifier, scalar classifier parameters, common context and
evaluation settings. It does not prescribe your approved class thresholds.

Supported initial classifiers:

| Classifier | Defaults |
| --- | --- |
| `logistic_regression` | lbfgs, max_iter=2000; numeric scaling |
| `decision_tree` | max_depth=5, min_samples_leaf=2 |
| `random_forest` | 100 trees, max_depth=6, min_samples_leaf=2, n_jobs=1 |

Both paired models use exactly the same classifier and configured parameters.
The evaluation seed supplies both model random states. Numeric imputation uses
training medians plus missing indicators; completely absent training columns use
sklearn's explicit zero fallback and retain a missing indicator. Categorical
imputation/encoding tolerates missing and unseen categories. All preprocessing is
fitted inside each pipeline on training observations only. No raw metric is
rewritten to an imputed value.

`prepare_cohort()`, `learner_split()`, `feature_set()`, `research_frame()` and
`fit_experiment()` are usable separately; `run_comparison()` orchestrates the
predeclared pair. Cohort target/class definitions must match the selected model.

One fixed GroupShuffleSplit is created once and shared by the pair. Default seed
42, test fraction 0.25 of learners, >=20 eligible observations and >=6 learners
are engineering guardrails, not a research sample-size/power calculation. Both
partitions must contain every configured class by default. There is no seed
search for better results. An explicit `require_all_classes_in_partitions=false`
can report an incomplete pilot: missing classes remain in metric definitions and
are listed in the report. Training still needs at least two observed classes.

**Primary metric: macro-F1 across all configured classes.** Reports also contain
per-class precision/recall/F1/support, ordered confusion matrices (rows actual,
columns predicted), balanced accuracy, majority baseline, class distributions,
observations/sessions/learners, missing-feature/exclusion counts, overlap checks
and the shared split manifest. Undefined precision/recall uses zero, explicitly
documented. Standalone balanced accuracy is null for single-class truth.

`macro_f1_difference_b_minus_a` and `comparison_outcome` (`improved`, `no_change`,
`worse`) report the actual comparison. Lack of improvement is explicitly reported.
No statistical significance, final full-data refit or real-data performance claim
is made. Choose algorithms/hyperparameters using an appropriate development
protocol later; repeatedly choosing the best held-out score is not a valid final
evaluation. This milestone supplies one pilot holdout, not nested CV or confidence
intervals.

## Run instructions

Use the existing Python 3.13 backend venv and optional `requirements-ml.txt`.
All synthetic observations remain in unit tests; none are distributed as real
research data. From the repository root in PowerShell:

```powershell
cd backend
New-Item -ItemType Directory -Path ../tmp -Force | Out-Null
$env:DATABASE_URL = 'sqlite+pysqlite:///:memory:'
.venv/Scripts/python.exe -m pytest tests/test_game_research_ml.py tests/test_game_ml.py -q -p no:cacheprovider --basetemp=../tmp/game-ml-research-tests
.venv/Scripts/python.exe -m ruff check app/modules/game/ml tests/test_game_research_ml.py tests/test_game_ml.py --no-cache
```

For a future audited local dataset, create a JSON config outside the repository.
The following class names are illustrative: replace them with your approved rubric.

```json
{
  "target": "difficulty",
  "class_labels": ["low", "medium", "high"],
  "classifier": "logistic_regression",
  "classifier_parameters": {},
  "common_context": [],
  "evaluation": {
    "primary_metric": "macro_f1",
    "random_state": 42,
    "test_size": 0.25,
    "min_examples": 20,
    "min_learners": 6,
    "require_all_classes_in_partitions": true
  }
}
```

```powershell
.venv/Scripts/python.exe -m app.modules.game.ml.research_cli `
  --dataset C:/local-research/audited-observations.json `
  --config C:/local-research/difficulty-config.json `
  --output C:/local-research/artifacts/difficulty-logreg-run-001 `
  --provenance "Audited export ID, collection window, exporter version and quality review" `
  --data-kind real_collected
```

This real-data command was not executed during the milestone. Synthetic CLI tests
use `--data-kind synthetic_development` and temporary output paths. For mastery,
choose `target=mastery` and its own explicit rubric classes. For the other algorithms,
choose `decision_tree` or `random_forest` with the same A/B parameters. Use a fresh
output directory for every experiment. The old `python -m app.modules.game.ml`
command remains the hint-only CLI.

## Artifacts, provenance and offline inference

Each comparison directory contains:

```text
comparison.json
score_only/model.joblib
score_only/metadata.json
score_plus_behaviour/model.joblib
score_plus_behaviour/metadata.json
```

Each metadata file records model/dataset/feature versions, target/cutoff and
score definition, selected features, classifier/actual parameters, training source
and synthetic/real kind, dataset hash, label assessment references/dates/rubrics,
runtime versions, actual held-out predictions/metrics and split details. Anonymous
unit/learner hashes support audit; raw student/session codes are not copied into
model metadata. Hashes are pseudonymous linkage, not guaranteed anonymization.

Models have version `game-research-{target}-{classifier}-v1`; the feature-set name
distinguishes A/B. The hint model retains its original versions. Save helpers
require fresh directories and never overwrite. Reports are written after models;
a failed save can leave an incomplete directory for inspection.

The existing `load_artifact()` gained optional expected-version arguments; its
hint defaults remain unchanged. `load_research_artifact()` supplies the research
versions and requires an explicit trusted-local flag. Checksums detect corruption,
not authenticity; joblib must never load uploaded/downloaded or other untrusted
objects. This extension serializes locally fitted sklearn pipelines only.

```python
from app.modules.game.ml.research_artifacts import load_research_artifact
from app.modules.game.ml.research_inference import predict_research

run = load_research_artifact(
    "C:/local-research/artifacts/difficulty-logreg-run-001/score_plus_behaviour",
    target="difficulty", classifier="logistic_regression",
    trusted_local_artifact=True,
)
result = predict_research(run, current_observation_export)
```

Inference ignores independent labels, accepts null labels and returns a class and
uncalibrated class probabilities. It is an offline validation helper; no production
endpoint is added.

## Remaining collection and PP1 dependencies

- Stable anonymous learner linkage across sessions/devices and across independent
  assessments; session/concept/phase mapping must match exactly.
- Approved independent difficulty/mastery rubrics, label sources, timing/protocol
  and quality review; meaningful real classes and adequate unseen learners.
- Audited complete task roster, explicit occurrence order and immutable content
  linkage; first-submission correctness/step denominators; abandoned-task evidence.
- Deduplicated errors/retries/hints/skips, complete hint coverage and reliable
  task durations. Existing success flags and reward stars cannot substitute.
- Audited observation cutoffs/export provenance; no automatic Supabase extractor
  is supplied. Existing database records cannot be assumed reliable or complete.
- Real paired training/validation, uncertainty/calibration and subgroup review;
  independent engagement/accessibility evaluation and PP1 research reporting.

The code and synthetic validation are ready for suitable audited local exports.
No real learner model, real-data accuracy, validated engagement/accessibility,
statistical significance or production inference is claimed.
# Real collection preparation (Milestone 2.2)

Current readiness: [Milestone 2.3.4](ML_Milestone_2_3_4.md) accepts timestamp ties
only with a validated recorded attempt counter and complete submission evidence.
Strict inversions, unsupported evidence and ownership quarantines remain blocked.
The immutable paired cohorts contain 30 retrospective / 9 prospective observations.
Retrospective preliminary training now passes the technical guards; prospective
training remains blocked. No models were trained in this milestone.

Previous preparation: [Milestone 2.3.3](ML_Milestone_2_3_3.md) imports the reviewed
50-session sheet through the unchanged guarded importer, validates all 16 separate
teacher assessments and prepares paired retrospective/prospective cohorts.
STU_008 uses the researcher-confirmed score-derived Intermediate label, preserving
its original conflicting source entry. Same-day ordering remains unknown.
Training stays blocked by an unresolved completed-session evidence check;
prospective evaluation also lacks sufficient learners and class coverage.
This milestone has no training option and performs no database operations.

Earlier continuation: [Milestone 2.3.1](ML_Milestone_2_3_1.md) isolates analytics
ownership conflicts only after shared integrity checks pass, revalidates the two
approved sessions and supplies the current 50-row review sheet. Training is still
blocked by cohort/class coverage, and no models were trained.

[Milestone 2.3](ML_Milestone_2_3.md) expands the candidate
roster to STU_001–STU_016 and excludes the accidental STU_0014 code without
reassignment or raw-data changes. It records the newer local export's counts
and evidence blockers. Current work remains preparation only, without training.

For researcher authenticity decisions, start with
[SESSION_VERIFICATION.md](SESSION_VERIFICATION.md): it documents the editable CSV,
allowed decisions, offline import validation and conditional training command.

See [ML_Milestone_2_2.md](ML_Milestone_2_2.md) for the verified-session CSV audit,
date-only teacher-label extension, local preparation command and current training
blocker. `collection_research` reads exported files only and requires exact
authenticity approvals. Unverified sessions never enter training. The optional
assessment provenance fields preserve after-gameplay timing and lesson revision
separately from the existing `pre_tutor`/`post_tutor` gameplay phase.
