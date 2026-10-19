# Game ML Milestone 2.4 - SYNTHETIC_DEVELOPMENT

Offline software validation only. No genuine learner data, teacher assessments,
production database connections, gameplay changes or inference endpoints.

## Source validation

Input: `C:/Users/new user/Downloads/synthetic_game_ml_200x2.zip`.
SHA-256: `008171f3f1d5ae61762b9dd1997382bce2852ebebd7f05dc6bf6193123df49d4`.

The supplied manifest, checksums, split, labels, session CSVs, convenience JSONs
and individual step rows are reconciled by `synthetic_development.py::read_synthetic_archive`.
Validated: 200 SIM learners, 400 unique sessions, two modes per learner,
3,600 unique task steps, one label/split per learner, 161 training learners
(322 sessions), 39 test learners (78 sessions), no learner overlap and no STU
observation identifiers. Overall simulated labels: Beginner 67, Intermediate 67,
Advanced 66. Every test class has 13 learners / 26 sessions.

The inspected supplied generator was rerun in a fresh ignored temporary directory
with seed 20261016. All records and manifest values reproduced. All six CSVs were
byte-identical; JSON/text comparisons allow Windows line-ending differences.
The adapter reads the bundled generator as data and never automatically executes it.

## Adapter and existing infrastructure

Real-data schemas, research training, artifact loading and inference modules remain
unchanged. The adapter reuses `ResearchObservation`, `IndependentLabel`,
`prepare_cohort`, `ResearchSplit`, `fit_experiment`, `save_comparison`,
`load_research_artifact` and `predict_research`.

- Reconstruct exact first-attempt score from complete step counts; check the
  rounded convenience score without passing its rounding error to the schema.
- Derive hinted steps from individual positive-hint rows. The supplied hint
  rate counts requests, and its capped hinted-step fraction is not a distinct-step
  fraction in 60 sessions. Preserve all raw values in the copied source files.
- The generator's `skipped_step_count` is the count of unfinished tasks.
  Preserve task-completion counts, but keep actual skipped-step features null.
- Sum serialized simulated step milliseconds for duration and its observation
  window; reconcile against raw duration/window within rounding precision.
  These are invented simulation times, never measured human response times.
- Keep game mode in observations/provenance. Both models use empty common
  context: Model A has score only; Model B has the same score plus the existing
  12 behavior fields. Two skipped-step fields remain unknown and use existing
  training-only missing-value preprocessing.
- Source labels are latent simulated classes, not teacher labels. The existing
  schema requires a source/date, so its `source=test` and fixed 2000-01-01 date
  are explicitly documented synthetic test-fixture scaffolding. They are not
  claims of a teacher, quiz or school test on that date and never enter features.
  Original blank assessment dates and simulated label-source fields remain intact.

`predefined_split` constructs the existing split object directly from supplied
learner assignments; it never invokes `GroupShuffleSplit` or searches seeds.
All six models share the exact 322/78 observation partition. Existing sample
guardrails and class-coverage checks are preserved. Preprocessing medians and
Logistic Regression scaling means are checked against training rows only.

## Configuration

Target: simulated mastery/proficiency; explicit class order Beginner,
Intermediate, Advanced. Classifier seed 42; generator seed 20261016.
The metadata test fraction is 39/200, reflecting the supplied partition.

| Classifier | Fixed configuration selected before evaluation |
|---|---|
| Logistic Regression | C=1.0, max_iter=2000, lbfgs; train-only scaling |
| Decision Tree | max_depth=5, min_samples_leaf=3 |
| Random Forest | 200 trees, max_depth=8, min_samples_leaf=2, n_jobs=1 |

No hyperparameter tuning or model selection based on held-out performance.
Each comparison also fits a majority-class baseline using training labels only.
All requested metrics use the 78 held-out synthetic sessions. They are correlated
within 39 learners and do not represent 78 independent people.

## Artifacts and offline inference

Output root: `exports/SYNTHETIC_DEVELOPMENT-game-ml-2-4-20261017-001/`.
Each algorithm has `score_only/` and `score_plus_behaviour/` bundles with
`model.joblib` and `metadata.json`, plus a paired `comparison.json`.
Bundles retain SYNTHETIC_DEVELOPMENT designation, synthetic data kind, adapter
and feature versions, fixed configuration, runtime versions, source fingerprints,
simulated-label provenance, split details and held-out evaluations. The serialized
pipeline itself also carries a synthetic designation.

The runner reloads its own newly saved local models using the existing explicit
trust/runtime/checksum checks. Held-out predictions are compared before and after
reload with both labels removed. Feature ordering and missing-behavior handling
are checked. `predict_synthetic` refuses genuine identifiers and requires synthetic
metadata. Raw source members and all adapted observations remain isolated here.

Completed results, exact artifact paths and validation appear below.

## Reproduction

From `backend/`, choose a new output directory that contains SYNTHETIC_DEVELOPMENT:

```powershell
.venv/Scripts/python.exe -B -m app.modules.game.ml.synthetic_development `
  --archive "C:/Users/new user/Downloads/synthetic_game_ml_200x2.zip" `
  --output "../exports/SYNTHETIC_DEVELOPMENT-game-ml-2-4-new-run"
```

Existing output directories are rejected. This CLI validates source checksums and
records; it does not automatically execute a supplied generator. The separately
audited regeneration evidence is retained in this milestone's validation metadata.

## Interpretation and future integration

The generator assigns classes before gameplay, then draws ability from
class-dependent centers (-1.1, 0, 1.1). Accuracy, errors, retries, hints, completion
and timing inherit those assumptions. Synthetic metrics measure how well models
recover the generator's design; they cannot validate real proficiency assessment,
educational benefit or Model B superiority on school students. Step correctness
uses simulated flags; no actual question/answer mathematics is supplied.

Keep these bundles offline. A future FastAPI service should load only an explicitly
approved genuine-data artifact after research validation and access-control review,
reject synthetic metadata, validate its feature contract and persist model/version
provenance separately from the existing heuristic result. No endpoint, database
schema or Game ending-screen integration is implemented by this milestone.

## Completed results - SYNTHETIC TEST RESULTS ONLY

All six bundles completed. Metrics use only 78 held-out synthetic sessions from 39 learners; each class has 26 sessions. Accuracy and balanced accuracy coincide because test classes are balanced.

| Algorithm | Model | Accuracy | Macro F1 | Balanced accuracy |
|---|---|---:|---:|---:|
| logistic_regression | A: score only | 0.653846 | 0.622564 | 0.653846 |
| logistic_regression | B: score + behavior | 0.615385 | 0.573770 | 0.615385 |
| decision_tree | A: score only | 0.679487 | 0.663371 | 0.679487 |
| decision_tree | B: score + behavior | 0.679487 | 0.677997 | 0.679487 |
| random_forest | A: score only | 0.679487 | 0.663371 | 0.679487 |
| random_forest | B: score + behavior | 0.653846 | 0.626811 | 0.653846 |

Majority baseline, fitted only on training labels: accuracy 0.333333, macro F1 0.166667 and balanced accuracy 0.333333. It predicts Beginner.

| Algorithm | Macro F1 change B minus A |
|---|---:|
| logistic_regression | -0.048794 |
| decision_tree | +0.014627 |
| random_forest | -0.036560 |

Model B improved macro F1 slightly for Decision Tree, with unchanged accuracy. It performed worse for Logistic Regression and Random Forest. No split or hyperparameter changes were made after seeing these results. There is no evidence of a general behavioral-feature advantage or real-student performance.

### Per-class precision and recall

| Algorithm | Model | Class | Precision | Recall | Support |
|---|---|---|---:|---:|---:|
| logistic_regression | A | beginner | 0.709677 | 0.846154 | 26 |
| logistic_regression | A | intermediate | 0.500000 | 0.269231 | 26 |
| logistic_regression | A | advanced | 0.666667 | 0.846154 | 26 |
| logistic_regression | B | beginner | 0.677419 | 0.807692 | 26 |
| logistic_regression | B | intermediate | 0.416667 | 0.192308 | 26 |
| logistic_regression | B | advanced | 0.628571 | 0.846154 | 26 |
| decision_tree | A | beginner | 0.709677 | 0.846154 | 26 |
| decision_tree | A | intermediate | 0.555556 | 0.384615 | 26 |
| decision_tree | A | advanced | 0.724138 | 0.807692 | 26 |
| decision_tree | B | beginner | 0.793103 | 0.884615 | 26 |
| decision_tree | B | intermediate | 0.517241 | 0.576923 | 26 |
| decision_tree | B | advanced | 0.750000 | 0.576923 | 26 |
| random_forest | A | beginner | 0.709677 | 0.846154 | 26 |
| random_forest | A | intermediate | 0.555556 | 0.384615 | 26 |
| random_forest | A | advanced | 0.724138 | 0.807692 | 26 |
| random_forest | B | beginner | 0.677419 | 0.807692 | 26 |
| random_forest | B | intermediate | 0.615385 | 0.307692 | 26 |
| random_forest | B | advanced | 0.647059 | 0.846154 | 26 |

### Confusion matrices

Rows are actual and columns predicted, both ordered Beginner, Intermediate, Advanced.

| Algorithm | Model | Matrix |
|---|---|---|
| logistic_regression | A | `[[22, 4, 0], [8, 7, 11], [1, 3, 22]]` |
| logistic_regression | B | `[[21, 4, 1], [9, 5, 12], [1, 3, 22]]` |
| decision_tree | A | `[[22, 4, 0], [8, 10, 8], [1, 4, 21]]` |
| decision_tree | B | `[[23, 3, 0], [6, 15, 5], [0, 11, 15]]` |
| random_forest | A | `[[22, 4, 0], [8, 10, 8], [1, 4, 21]]` |
| random_forest | B | `[[21, 3, 2], [8, 8, 10], [2, 2, 22]]` |

Majority baseline matrix: `[[26,0,0],[26,0,0],[26,0,0]]`. Baseline per-class precision/recall: Beginner 0.333333/1.0; Intermediate 0/0; Advanced 0/0. Zero undefined precision is explicit.

### Exact model paths

Each path below has a sibling metadata.json with synthetic designation, source/version/configuration/runtime/feature/test information:

- `exports/SYNTHETIC_DEVELOPMENT-game-ml-2-4-20261017-001/decision_tree/score_only/model.joblib`
- `exports/SYNTHETIC_DEVELOPMENT-game-ml-2-4-20261017-001/decision_tree/score_plus_behaviour/model.joblib`
- `exports/SYNTHETIC_DEVELOPMENT-game-ml-2-4-20261017-001/logistic_regression/score_only/model.joblib`
- `exports/SYNTHETIC_DEVELOPMENT-game-ml-2-4-20261017-001/logistic_regression/score_plus_behaviour/model.joblib`
- `exports/SYNTHETIC_DEVELOPMENT-game-ml-2-4-20261017-001/random_forest/score_only/model.joblib`
- `exports/SYNTHETIC_DEVELOPMENT-game-ml-2-4-20261017-001/random_forest/score_plus_behaviour/model.joblib`

### Offline inference and tests

All 468 held-out predictions (78 sessions x six models) match before/after artifact reload and after removing both label fields. This confirms expected model outputs survive reload and labels are not used as predictors; it does not mean every prediction matches simulated truth. Feature ordering and missing-behavior inference passed for all six bundles. No new split or full-dataset refit occurred.

The 11 focused adapter tests passed. Existing ML/collection/session regression selection: 202 passed, five collection training-path cases deselected. Total: 213 passed. Regression fitting was restricted to synthetic_development and PostgreSQL connections were forbidden. Ruff and git diff --check passed. Existing dependencies were reused.

Changed/added source files:

- `backend/app/modules/game/ml/synthetic_development.py` (isolated validation, adapter, predefined-split runner and synthetic-only inference wrapper).
- `backend/tests/test_game_synthetic_development.py` (11 portable invented-fixture cases; no external school data).
- `backend/app/modules/game/ml/ML_Milestone_2_4.md` (this report).

Other ML modules and schemas are reused unchanged. All experiment outputs are isolated under the SYNTHETIC_DEVELOPMENT root. Genuine datasets and previous review decisions are not inputs to this run. No database, hosting or Game ending-screen integration was performed.
