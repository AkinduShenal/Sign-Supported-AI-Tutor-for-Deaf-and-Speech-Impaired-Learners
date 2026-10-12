# ML Milestone 1.1 — completed work record

Component: Member 3, Game-Based Learning Analytics.
Recorded: October 12, 2026. PP1 deadline: October 22, 2026.
Status: **offline implementation and synthetic engineering verification complete**.
Real-data validation, final research models and production inference are incomplete.

## Scope and research alignment

The approved primary hypothesis compares a gameplay score-only classifier with
the same classifier using score plus behaviour, against independent difficulty
or concept-mastery labels on unseen learners. Macro-F1 is the primary metric.
The previous next-task hint experiment remains an auxiliary experiment.

The attachment initially ended midway through Task 7. The researcher supplied
the remaining provenance, test, strict-scope and completion requirements during
implementation; those requirements were incorporated, including explicit tests
for mismatched student/session/concept labels.

## Implementation delivered

1. A separate versioned learner–concept–assessment-session observation contract,
   including observation timestamps, activity identifiers, audited metrics and
   independently assessed difficulty/optional mastery labels.
2. Independent labels require matching learner/session/concept/phase identities,
   teacher/quiz/test source, source reference, timezone-aware assessment date,
   rubric version and an independence assertion. No heuristic labels are generated.
3. An explicit gameplay score: first-attempt correct steps / all planned steps.
   Missing/unaudited evidence remains unavailable. Success flags, local stars and
   heuristic mastery never supply this score or the independent target.
4. A conservative aggregator for validated original TaskRecord inputs: weighted
   numerator/denominator sums, complete task roster, abandoned/final task retention,
   null propagation, exact skipped-step coverage and duration reliability gates.
5. Predeclared score-only and score-plus-behaviour feature sets with identical
   optional context. Behaviour includes errors, retries, hints, completion, skipped
   steps and reliable duration. Label/identity/future assessment fields are excluded.
6. Configurable target, class order, classifier/parameters and evaluation settings;
   Logistic Regression, Decision Tree and Random Forest sklearn pipelines.
7. One eligible cohort and one learner-separated split shared by both models.
   Missing behaviour is imputed only from training observations, without changing
   Model B participants. Model A uses exactly the score/context subset of Model B.
8. General binary/multiclass metrics, macro-F1 difference, honest no-improvement
   reporting, majority baseline, class-level metrics and confusion matrices.
9. Per-model provenance, label references/rubrics/dates, feature definitions,
   classifier parameters, dataset hash, shared split, actual evaluations and held-out
   predictions. New artifacts are separate from hint artifacts and refuse overwrite.
10. Local JSON comparison CLI and offline research inference. Existing hint entry
    point, feature contract, training semantics and tests remain preserved.

## Files created or modified in this milestone

All ML paths below are relative to `backend/app/modules/game/ml/`.

| File | Change / purpose |
| --- | --- |
| `ML_Milestone_1.md` | Created historical Milestone 1 implementation/review record |
| `ML_Milestone_1_1.md` | Created this completion record |
| `research_schema.py` | Created independent-label/session contract and validation |
| `research_dataset.schema.json` | Created generated machine-readable contract |
| `research_dataset.py` | Created aggregation, feature sets and availability logic |
| `research_training.py` | Created configurable paired training/evaluation |
| `research_artifacts.py` | Created paired saving and research-version loading |
| `research_inference.py` | Created offline multiclass inference |
| `research_cli.py` | Created separate research comparison entry point |
| `RESEARCH_README.md` | Created dataset, methodology, run and limitation guide |
| `README.md` | Added research guide and milestone-record links; retained hint documentation |
| `artifacts.py` | Added optional expected-version loader arguments; original hint defaults retained |
| `backend/tests/test_game_research_ml.py` | Created 70 synthetic research tests |

No edits were made to original `schema.py`, `dataset.py`, `training.py`,
`inference.py`, `__main__.py`, `task_dataset.schema.json`, `requirements-ml.txt`
or `backend/tests/test_game_ml.py` during Milestone 1.1. Existing unrelated
uncommitted changes were preserved. No shared dependency, database, API, Phaser,
UI, Quiz, Tutor, Avatar or Remedial contract was altered.

## Reused functionality

- Original TaskRecord identity/count/order validation for aggregation inputs.
- Original FeatureExtraction availability/result type.
- Original TrainingRun, TrainingDataError and runtime-version collection.
- Existing fresh-directory save_artifact lifecycle, checksum/trust gates and
  version checking. Loader defaults remain compatible with hint artifacts.
- Existing pinned sklearn/numeric environment; no new dependency was needed.

## Verification commands and exact results

Commands were executed from `backend/`, after creating the ignored parent `tmp/`
directory, with `DATABASE_URL=sqlite+pysqlite:///:memory:`. ML tests do not import
the application database/configuration or contact a live service.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_game_research_ml.py tests/test_game_ml.py -q -p no:cacheprovider --basetemp=../tmp/game-ml-milestone-1-1-final
```

**125 passed in 11.31s**: 70 new research tests and all 55 original hint tests.
Coverage includes independent-label identity/source validation, missing labels,
score aggregation, leakage protection, identical cohorts/splits, binary/multiclass
metrics, training-only preprocessing, all three classifiers, no-improvement cases,
artifact provenance/version compatibility, inference and both CLI workflows.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_game_sessions_api.py -q -p no:cacheprovider
```

**25 passed in 2.45s**, with one existing Starlette/httpx deprecation warning.
This verifies preservation of the existing Game API/heuristic behaviour.

Ruff check passed and formatting check passed across all 15 ML/test Python files.
`git diff --check` passed. The generated research JSON Schema matches the Pydantic
contract in a passing unit test. These checks are scoped to Game ML and its API;
they are not a claim that the entire application's test suite was executed.

## Synthetic pipeline result — not research performance

The invented fixture contains 12 synthetic learners, 24 sessions and 72
learner–concept–assessment observations, with 24 examples per illustrative class.
Seed 42 splits 9 learners / 54 observations into training and 3 learners / 18
observations into test, with zero learner overlap and identical A/B labels.

The CLI Logistic Regression validation artifact records:

| Synthetic metric | Model A: score-only | Model B: score + behaviour |
| --- | --- | --- |
| Macro-F1 | 0.166667 | 1.0 |
| Balanced accuracy | 0.333333 | 1.0 |
| Confusion matrix, labels [low, medium, high] | `[[0,0,6],[0,0,6],[0,0,6]]` | `[[6,0,0],[0,6,0],[0,0,6]]` |

The majority baseline macro-F1 is 0.166667. The synthetic B-minus-A difference
is 0.833333. Scores were deliberately constant and synthetic behaviour separable
to exercise the comparison; **this is not evidence that behaviour improves real
learner classification**. A separate constant-behaviour test verifies a zero
difference and explicit no-improvement reporting. All three candidate algorithms
were exercised by unit tests; no final classifier was selected.

Temporary paired artifacts live under ignored `tmp/game-ml-milestone-1-1-final/`.
No model was checked into Git or written over an existing researcher artifact.
See [RESEARCH_README.md](RESEARCH_README.md) for the permanent run instructions.

## Limitations and remaining PP1 dependencies

- Label independence and complete observation rosters require actual external
  auditing; a Boolean assertion cannot establish scientific validity.
- Approved difficulty/mastery class rubrics, matching assessment sources/dates,
  stable anonymous identity and enough independently labelled unseen learners.
- Reliable ordered task rosters, first-submission correctness/denominators,
  deduplicated events, abandoned-task completion, hint coverage, skipped-step
  evidence and reliable durations. Existing persisted defaults are not evidence.
- Audited cutoff-based local exports. There is no automatic database exporter or
  collection repair in this milestone, and no shared schema change.
- Real comparative evaluation, sample-size justification, uncertainty/calibration,
  appropriate algorithm-selection protocol and subgroup/accessibility review.
- Engagement indicators are descriptive; engagement diagnosis and visual-first
  accessibility evaluation still need study design and real participant evidence.

Ready for later real training: validated local observation input, score/behaviour
preparation, paired pipelines for all three classifiers, grouped evaluation and
artifact provenance. Pending for PP1: approved labels, reliable real collection,
audited export, real-data pilot analysis and carefully qualified research reporting.

No production Supabase connection, migration, real-data/final model training,
production inference, commit, push or branch switch occurred in this milestone.
