**Milestone 2.5 — protected experimental Game inference.**

Endpoint: `GET /api/v1/game/sessions/{game_session_id}/ml-prediction`.

This route is disabled by default. No token, live-session approval, deployment setting or database record is created by the implementation. `ml_preview.py`, the existing analytics/scoring/recording workflow, `game-heuristic-v1`, frontend, model weights, evaluation metrics and teacher labels remain unchanged. The only existing application-file edit is adding this subrouter to the Game router. Importing this integration does not load the model or import the model's numerical libraries.

**Final audit and integration boundary.**

The strict saved-session portion of the separate adapter prototype is integrated in `legacy_adapter.py`; the historical CSV reconstruction path is deliberately excluded. It calls the unchanged `read_ml_input_preview`, requires complete validated features and a completed saved six-task session, and reconciles all saved aggregates using the unchanged `calculate_session_features`. Missing first outcomes, invalid chronology, incomplete coverage and inconsistent saved values fail closed. The preview's existing readiness flag is not changed: an explicitly approved legacy contract is a separate research authorization prerequisite.

Legacy inputs retain exactly the frozen order. Accuracy, success rate and average attempts are rounded to three decimals. Counts and saved whole elapsed seconds are retained. Legacy `game_hint_rate` is `round(total_hint_count / tasks_total, 3)` and can exceed 1; the saved/backend hinted-task fraction is never overwritten. One session produces one input row. The service never pools extra sessions, invents payloads, imputes missing evidence or falls back to a heuristic.

The historical 18-record comparison establishes numerical reconstruction, not complete genuine-session validation: those CSV files omit original task summaries and full event payloads. They cannot authorize inference. The original 12 multi-session learner observations and the 170 simulations remain limitations of the existing experiment. The manifest requires a reviewer to explicitly accept the named legacy contract for each approved scope. That is research access approval, not a claim that feature semantics or real-world proficiency accuracy have been independently validated.

**Authentication, approvals and response privacy.**

A separate `GameMLResearchBearer` credential is required. Disabled configuration returns 503. When enabled/configured, missing or invalid credentials return 401 before manifest/session access. Tokens must be at least 32 characters and cannot equal the CSV export key. Tokens belong in the Authorization header, not URL parameters or frontend bundles. The CSV export credential never grants prediction access.

After authentication, a local approval manifest must match its separately configured SHA-256. Every approved entry binds exactly:

```json
{
  "game_session_id": "EXACT_REVIEWED_SESSION_ID",
  "student_code": "STU_999",
  "concept_id": "linear_equations",
  "learning_cycle_id": "00000000-0000-0000-0000-000000000000",
  "assessment_phase": "pre_tutor"
}
```

This is an illustrative binding, not approval of a learner or session. Copy the example manifest to a private local location, fill its reviewer/reference/time, populate only explicitly reviewed bindings and current exclusion/quarantine lists, and set `legacy_contract_accepted=true` only after that review. The committed example deliberately has false acceptance and no approved sessions, so it cannot enable predictions. Duplicate approvals, malformed student codes (`^STU_[0-9]{3}$`), unknown contract fields and bad manifest pins are rejected. The two known historical ownership-conflict quarantines and three development IDs are always denied in addition to manifest exclusions. Future quarantines must be carried into the reviewed manifest; there is no automatic provenance reassignment.

Unapproved/excluded/quarantined sessions return the same 404 response before database lookup. A recorded identity/concept/cycle/phase mismatch also returns a generic 404. Incomplete or inconsistent approved evidence returns a generic 422. Model/runtime/configuration failures return a generic 503. No error includes a session, learner, internal path, pickle exception or traceback. Successes and controlled failures use `Cache-Control: no-store`.

Researcher authorization resolves before the database dependency. PostgreSQL reads use a fresh `REPEATABLE READ READ ONLY` transaction; pending mutations/pre-existing transactions are refused. SQLite is supported for isolated snapshot/tests. Evidence projection uses `no_autoflush`; the read transaction is rolled back/released before model execution. No commit, flush, result creation, session completion or row update is performed. This route does not provide authenticated learner access and does not change any existing route's authentication policy. Use protected local/private research hosting and TLS for remote access; no deployment changes are included.

**Isolated model runtime.**

The API runtime currently has different NumPy/pandas/SciPy versions from the export. It therefore launches `worker.py` using an explicitly configured separate interpreter with `-I -B`, a dedicated working directory, bounded timeout and a minimal environment without researcher/DB/application credentials. The worker receives only the nine numeric features. Socket operations are denied inside the worker. It never installs packages, downloads artifacts, extracts ZIP members, fits a model or writes output files.

Before deserializing the trusted local artifact, every worker verifies SHA-256 pins for the model, original metadata, verification report and frozen fixtures, checks the exact feature/class order and experimental provenance, and checks all five dependency versions. The model pin is:

`6083d2b4f73661c73e192238d3ecd926618d87be1dad3bdd33800f0d89712ff6`

The expected bundle is the supplied `game_ml_model_export_with_fixtures.zip`. Pinning metadata and fixtures preserves the presented metrics and provenance as well as the weights. A different model/bundle is not silently accepted. The loaded pipeline must be median imputation -> StandardScaler -> Logistic Regression, with the frozen feature/class order. Input evidence must be complete despite the fitted imputer's existence.

The validated isolated runtime is Python **3.13.12**, scikit-learn **1.6.1**, NumPy **2.1.3**, pandas **2.2.3**, SciPy **1.16.3**, joblib **1.6.0**. Original metadata preserves the Colab Python **3.13.16** patch; this patch difference was explicitly exercised by frozen reproduction. Only the tested 3.13.12 runtime is accepted by this integration. No shared backend requirement or installed dependency was changed.

Every worker process reproduces all ten frozen labels and their thirty probabilities at `atol=1e-12, rtol=0` before serving an actual prediction. It validates predicted classes and finite, normalized class probabilities. The original evaluation is returned unchanged as metadata; probabilities are model estimates, not claimed calibrated confidence or teacher verification. The subprocess timeout is bounded; no resident model service or automatic restart/download flow is introduced.

**Configuration (not applied).**

All settings are separate research options in `ResearchMLSettings`; existing deployment configuration was not edited:

```text
GAME_ML_EXPERIMENTAL_ENABLED=false
GAME_ML_RESEARCH_TOKEN=<dedicated researcher secret, distinct from export key>
GAME_ML_SESSION_MANIFEST=<absolute path to reviewed private JSON manifest>
GAME_ML_MANIFEST_SHA256=<lowercase SHA-256 of the reviewed manifest bytes>
GAME_ML_MODEL_ARCHIVE=<absolute path to game_ml_model_export_with_fixtures.zip>
GAME_ML_PYTHON=<absolute path to the compatible isolated Python executable>
GAME_ML_TIMEOUT_SEC=30
```

The existing local audited interpreter is under `local_ml_artifacts/compatibility_audit/env/Scripts/python.exe`. The service stays unavailable when any required configuration is absent/invalid. Setting the enabled flag alone is insufficient. This implementation supplies no real credentials or real approvals and leaves the flag at its default false.

An operator who has completed the research review can use the ordinary bearer request:

```text
GET /api/v1/game/sessions/<approved-session-id>/ml-prediction
Authorization: Bearer <dedicated-research-token>
```

Success includes `status=experimental_prediction`, actual `predicted_level`, class probabilities for Beginner/Intermediate/Advanced, `model_name`, `model_version`, `model_status=EXPERIMENTAL_NOT_PRODUCTION_APPROVED`, `teacher_verified=false`, `feature_source=validated_saved_game_session`, `feature_contract`, `model_checksum`, original `model_metadata` and the actual isolated `runtime`. No student/session identity or input evidence is returned. `game-ml-experimental-v1` is this integration's identifier; the original model metadata has no training-version field and is preserved verbatim.

**Verification and limits.**

Tests in `backend/tests/test_game_research_inference.py` cover the credential/configuration/manifest boundary, all binding fields, known and operator exclusions, incomplete and inconsistent evidence, invalid chronology, missing/malformed payloads, checksum/model/runtime failures, feature/class order, all ten frozen predictions, the 18 historical adapter projections and actual-model end-to-end predictions for both strict synthetic game modes. Full-path predictions must exactly equal offline worker predictions, preserve stored rows/heuristics, and execute SELECTs only. Private artifact/workbook tests skip in clean environments lacking the trusted local files; no substitute artifact is generated or downloaded. Actual local execution results are documented in the final milestone report.

No live production record was queried or approved by these tests. The live PostgreSQL transaction mode remains unexercised here. The historical CSV is insufficient to prove strict genuine-session eligibility, and synthetic end-to-end success is software validation rather than real-world proficiency validation. Actual activation remains blocked until the researcher supplies the reviewed access configuration and validates complete genuine saved evidence. No frontend, scoring, content or production rollout is part of this milestone.
