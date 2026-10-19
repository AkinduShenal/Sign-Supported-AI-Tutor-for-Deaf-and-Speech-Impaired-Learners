# Game ML Milestone 2.2 — verified data preparation

Continuation: [researcher session verification](SESSION_VERIFICATION.md) provides
the editable CSV sheet, validated offline import and latest training status.
The original preparation results below remain the historical baseline.

Recorded October 16, 2026 (Asia/Colombo). Data preparation and compatibility work
are implemented. **Real training is blocked; no real models, accuracy results or
real offline predictions were produced.** Milestones 1 and 1.1 remain available.

## Source and decisions

Read-only source: `C:/Users/new user/Downloads/game-collection-2026-10-15T18-41-34-162Z.zip`.
No database connection, migration, scoring change or UI change was used.
The ZIP contains 286 sessions, 325 answer outcomes, 1,912 events and 15 session
analytics records. Its manifest reports 132 task summaries, but those summaries
are **not included as a CSV**. All source hashes are recorded in the generated audit.

Among STU_001–STU_007 there are 19 sessions: 11 completed and 8 incomplete.
Researcher confirmation authorizes only the following two exact matching sessions:

| Session ID | Student | Mode | Answers | Events | Session summaries | First-attempt score |
|---|---|---|---:|---:|---:|---:|
| ff5f50f3-5dc3-4aaf-9f45-168ccd92ee2b | STU_006 | drag_drop | 15 | 61 | 1 | 5/10 = 0.50 |
| e0cb4176-562a-42e3-86d5-eb6fc0b123dc | STU_007 | hangman | 18 | 68 | 1 | 3/6 = 0.50 |

The 17 other target-learner sessions remain **REVIEW REQUIRED**, including all
STU_001–STU_005 sessions. Their dates neither approve nor exclude them.
The 264 sessions outside the requested cohort also remain unverified and are
not training inputs. Only `GAME-SES-2026-001`, `GAME-SES-2026-002` and
`GAME-SES-2026-003` receive **EXCLUDED DEVELOPMENT**. No source records are deleted.

The output includes a complete 286-row `session_review.csv`, plus a readable
22-row `session_review.md` for the 19 requested-learner sessions and three exact
development exclusions. Each row records exact IDs, learner, mode, completion,
answer/event/session-summary counts and the inclusion decision/reason.

## Assessment compatibility

The researcher confirmed a separate teacher-administered 10-question Simple
Linear Equations assessment on **October 15, 2026**, after gameplay, with a short
Simple Equations lesson revision before assessment. The exact time was not recorded.
The label source is the researcher's confirmed teacher report; original assessment
sheets were not supplied and no claim of independent document verification is made.

| Learner | Teacher score | Proficiency | Verified eligible gameplay |
|---|---:|---|---|
| STU_001 | 3/10 | beginner | None; review required |
| STU_002 | 6/10 | intermediate | None; review required |
| STU_003 | 5/10 | intermediate | None; review required |
| STU_004 | 6/10 | intermediate | None; review required |
| STU_005 | 9/10 | advanced | None; review required |
| STU_006 | 7/10 | intermediate | One verified session |
| STU_007 | 4/10 | beginner | One verified session |

`IndependentLabel` now accepts either its original timezone-aware `assessed_at`
or an explicit date-only `assessed_on`. These labels use `assessed_at=null` and
`assessed_on="2026-10-15"`; no midnight or other timestamp is invented.
Both absent, naive timestamps and contradictory dates are rejected.

Optional audit-only fields preserve `assessment_timing="after_gameplay"`,
`revision_before_assessment`, `revision_description`, `assessment_score` and
`assessment_max_score`. Original `pre_tutor`/`post_tutor` values retain their
meaning. The exported gameplay phase is `pre_tutor` and remains `pre_tutor` in
the observation and its linked label; it does not describe the assessment's timing.

The existing `mastery_label` target slot represents this operational measure:
**teacher-assessed Simple Linear Equations proficiency after gameplay and revision**.
It is not evidence of isolated pre-revision mastery, nor a second difficulty label.
Class order is beginner/intermediate/advanced; rubric ranges are 0–4/5–7/8–10.
Teacher scores, class labels, assessment dates and revision information never enter
the selected model predictors. Game heuristic classifications are never labels.

Existing timestamp-based datasets/artifacts still load. The generated JSON schema
includes the optional provenance extension; older consumers must update before
reading the new date-only records. Gameplay metric and predictor versions remain
unchanged; no feature was renamed or silently added to existing artifacts.

## Feature preparation and evidence

The new offline `collection_research` command reads either the existing ZIP or
CSV directory and requires an explicit exact-session review file. It uses existing
`ResearchObservation`, feature selection, cohort preparation and learner-split code.
No automatic session approval is inferred from a code, date, prefix or completion.

Checks reconcile source/client IDs, recorded learner/context links, export manifest
counts, answer-event projections, numbered attempts, first-attempt correctness,
expected/submitted responses, frozen variant/activity/difficulty rosters, shown
steps, completion events, hints-before-attempt, hint/retry totals and saved summaries.
Drag & Drop completion events describe operation steps; Hangman completion events
describe final-value tasks. A failed Hangman task can still be completed; completion
is not success. A missing Hangman step index uses its documented single-step protocol;
a missing Drag & Drop step index is rejected.

For this export there are no duplicate source/client IDs, orphan source-session
links or inconsistent recorded learner joins. Legacy answers with missing attempt
numbers are recorded as unavailable evidence, not incorrectly deduplicated as if
their empty numbers identified the same submission. None enter the verified dataset.
Complete per-step rosters prove zero skipped steps for the two included observations;
absent or incomplete evidence is never converted to a measured zero.

Model A uses exactly `gameplay_score`. Model B uses that same score plus the existing
12 behavioural predictor fields. Both feature files contain the exact same two
learner/session units. Student/session columns in those files are linkage metadata;
the pipeline selects only the declared predictor names.

| Verified learner | Wrong attempts | Retries | Hint requests | Hinted steps | Completed tasks |
|---|---:|---:|---:|---:|---:|
| STU_006 | 5 | 5 | 3 | 3/10 | 6/6 |
| STU_007 | 13 | 12 | 5 | 3/6 | 6/6 |

Timing is unavailable to both models: raw active-time summaries and wall-clock
elapsed time do not establish reliable active task timing/focus coverage.
`task_duration_seconds` and `duration_per_step` remain null. No imputed values
are substituted into raw observations.

Each verified session has two easy, two medium and two hard activities. This
activity difficulty is preserved in `source_links.json`, distinct from learner
proficiency. Milestone 1.1's fixed feature schema excludes activity difficulty
predictors; this milestone preserves that contract. A future feature-version change
is needed to make difficulty composition a predictor. Its composition is constant
in these two sessions anyway.

Every observation links to source session/result/event/answer IDs and export hashes.
A frozen current variant catalog is reconciled against actual expected responses
and step/activity identifiers. Historical `content_version` is missing in all 33
verified answers; the current catalog and saved-completeness assertion are documented
evidence, not a claim of a recovered historical content version. Task-summary rows
and reliable task timing remain collection/export dependencies.

## Training decision and outputs

Verified learner distribution: **beginner 1, intermediate 1, advanced 0**.
This differs from the seven supplied teacher labels (2/4/1): unverified gameplay
cannot be promoted into the training cohort to restore the desired distribution.
Multiple sessions never count as additional independent learners.

Training is blocked by missing Advanced gameplay and by the unchanged training
guardrails (20 observations, six learners, all configured classes in both grouped
partitions). Even relaxed sample guardrails cannot create a valid train/test
evaluation from two learners, each with a different class. With only one Advanced
learner among all seven, a split containing Advanced in both partitions is impossible.
No seed search, synthetic teacher label or row-level split is used to force a fit.

The two verified score-only values are identical. Each learner played a different
mode, so mode and class are confounded in this tiny cohort. No reliable accuracy,
cross-validation, engagement diagnosis or superiority conclusion is supported.

The final local output is `exports/ml-milestone-2-2-20261016-run-004/`.
Earlier runs are retained as diagnostics; use run 004 for the final audit.
The final directory contains:

- `session_review.csv` and `.md`: exact decisions for source sessions.
- `audit.json`: source checks, counts, per-learner eligibility and missing evidence.
- `cleaned_observations.json`: only verified, evidence-compatible observations.
- `source_links.json`: raw evidence references, mode semantics and limitations.
- `teacher_label_matching.json` and `teacher_assessment_provenance.json`.
- `score_only_features.json` and `score_plus_behaviour_features.json`.
- `review_input.json`, `experiment_config.json`, `training_feasibility.json` and `training_status.json`.

These real-data outputs and the review input remain under the already ignored
repository-root `exports/` directory. Prior diagnostic runs are retained and never
overwritten. No `experimental_models` directory or real offline predictions exist.
When a future reviewed cohort passes all gates, `--train` reuses the existing paired
pipeline, saves PRELIMINARY/EXPERIMENTAL artifacts into a fresh subdirectory and
checks local reload plus label-free predictions. Such predictions on input records
verify engineering operation; they are not independent evaluation results.

## Reproduction

The frozen review input is `exports/ml-milestone-2-2-inputs/confirmed-review.json`.
It contains the two explicit session approvals, researcher-reported teacher scores,
provenance and frozen variant catalog. Preserve it with the source export. From
the repository root in PowerShell:

```powershell
cd backend
.venv/Scripts/python.exe -m app.modules.game.ml.collection_research `
  --export "C:/Users/new user/Downloads/game-collection-2026-10-15T18-41-34-162Z.zip" `
  --review ../exports/ml-milestone-2-2-inputs/confirmed-review.json `
  --output ../exports/ml-milestone-2-2-reproduction-001 `
  --train
```

Choose a fresh output path each time. Successful preparation exits zero while
reporting `BLOCKED` and `NOT TRAINED` when training gates fail. It never overwrites
a prior run. Omit `--train` for preparation only. No database settings are needed.
An optional `--training-config` takes an existing `ExperimentConfig` JSON; the
collection command requires the declared proficiency classes, `mastery` target
and empty common context. Existing research CLI/algorithms remain unchanged.

Engineering checks use only invented test fixtures and isolated SQLite:

```powershell
$env:DATABASE_URL = 'sqlite+pysqlite:///:memory:'
.venv/Scripts/python.exe -m pytest tests/test_game_collection_research.py tests/test_game_research_ml.py tests/test_game_ml.py tests/test_game_sessions_api.py tests/test_game_collection_download.py tests/test_game_export_cli.py -q -p no:cacheprovider --basetemp=../tmp/game-ml-22-tests-reproduction-001
.venv/Scripts/python.exe -m ruff check app/modules/game/ml tests/test_game_collection_research.py tests/test_game_research_ml.py tests/test_game_ml.py --no-cache
```

Synthetic tests cover date-only/legacy label compatibility, exact exclusions,
uncertain sessions, linkage/duplicate/missing evidence, scoring, feature separation,
leakage prevention, equal cohorts, blocked fitting and no-overwrite outputs. Gated
artifact reload and label-free inference are tested for Logistic Regression,
Decision Tree and Random Forest using explicitly synthetic development provenance.
Existing Milestones 1/1.1 tests retain their learner splits, training-only
preprocessing, metrics and original hint-experiment checks. Synthetic results are
engineering verification only.

Actual verification: **197 passed** in 16.78 seconds for the six listed test
modules; one existing Starlette/httpx deprecation warning. Ruff passed for the ML
package and related ML tests. `git diff --check` passed. A separate final assertion
confirmed the source ZIP checksum was unchanged, exactly the two approved sessions
were included, both feature sets had identical units, timestamps remained null for
date-only labels and no real model artifacts existed.

Repository files created: `collection_research.py`, this milestone record and
`backend/tests/test_game_collection_research.py`. Files modified:
`research_schema.py`, its generated `research_dataset.schema.json` and
`RESEARCH_README.md`. Real source-linked outputs/review inputs are local ignored
files under `exports/`. The unrelated untracked `CLAUDE.md` was preserved.

## Next milestone 2.3 / PP1

Resolve the 17 target-session authenticity decisions against the collection log
using exact IDs; prioritize the only Advanced learner, STU_005. Preserve the
assessment revision/timing limitation and obtain original assessment references
where possible. Collect additional independently labelled learners, especially
Advanced, before designing a class-covered learner-separated evaluation.

Add an authorized read-only export of task summaries, original event payloads and
content versions if available; improve prospective focus/timing capture separately
from gameplay scoring. Freeze the inclusion policy and experimental feature version
before interpreting a comparison. For PP1, present the verified data audit and
working offline pipeline with its explicit training blocker. Do not integrate a
prediction into the Game ending screen or present synthetic metrics as findings.
