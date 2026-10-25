**Milestone 2.5 final status: PARTIAL — protected integration implemented; live activation remains blocked.**

Software verification passed. The route remains disabled by default. No production session was queried, approved or used for inference, and no credentials/deployment settings were configured. Historical incomplete CSV records were never promoted into full saved-session evidence. Actual researcher-approved live activation requires the access configuration and full genuine evidence described below.

**Files created.** Under `backend/app/modules/game/research_inference/`: `__init__.py`, `contract.py`, `legacy_adapter.py`, `access.py`, `worker.py`, `service.py`, `router.py`, `approved_sessions.example.json`, `README.md`, and this report. New test file: `backend/tests/test_game_research_inference.py`.

**Existing file modified:** `backend/app/modules/game/router.py`, adding the research subrouter import and registration. Its existing preview changes were preserved. No other existing application source was edited. Existing `ml_preview.py`, scoring/heuristics, Game mechanics, recording, frontend, tables/migrations and question logic are unchanged. The pre-existing legacy prototype remains intact and is still tested independently.

**Exact endpoint:** `GET /api/v1/game/sessions/{game_session_id}/ml-prediction`.

**Authentication/configuration:** `GAME_ML_EXPERIMENTAL_ENABLED` defaults to false. When explicitly enabled, a dedicated `GAME_ML_RESEARCH_TOKEN` (minimum 32 characters, distinct from the effective CSV export key) must authenticate before any session lookup. A private approval manifest must be supplied through `GAME_ML_SESSION_MANIFEST` and pinned by `GAME_ML_MANIFEST_SHA256`. It binds each approved session to an exact student code, concept, learning cycle and assessment phase, plus explicit legacy-contract acceptance and exclusion/quarantine lists. The example approves no sessions and has false contract acceptance. Known historical quarantines/development IDs cannot be approved. Actual recorded context must match the manifest and student codes must match `^STU_[0-9]{3}$`.

The operator must also provide absolute trusted paths through `GAME_ML_MODEL_ARCHIVE` and `GAME_ML_PYTHON`. `GAME_ML_TIMEOUT_SEC` defaults to 30 seconds and is bounded to 1-60 seconds. No settings were applied. The configured archive must be the frozen bundle with fixtures; a different model or modified metadata is rejected. Full instructions and the non-active manifest example are in `README.md`.

**Data/model path:** authenticated manifest binding -> repeatable read-only PostgreSQL snapshot (SQLite in tests) -> strict unchanged preview -> saved aggregate reconciliation -> separately copied legacy projection -> release transaction -> isolated Python worker -> verified frozen pipeline prediction. No CSV fallback, imputation of missing evidence, arbitrary client feature JSON, new sessions, data writes or heuristic substitution is permitted. All controlled responses use `Cache-Control: no-store`, and errors do not expose identities or internal paths. Success returns actual model classes/probabilities, the requested experimental flags, feature source/contract, frozen checksum, original metadata and runtime; it contains no student/session identifiers.

**Frozen artifact preserved:** model SHA-256 `6083d2b4f73661c73e192238d3ecd926618d87be1dad3bdd33800f0d89712ff6`. Separate member checksums pin original metadata, verification and fixtures, preserving the supervisor-presented evaluation values. The model version in the response, `game-ml-experimental-v1`, identifies this integration; it is not a retraining/version claim added to the original metadata.

**Compatible isolated runtime verified:** Python 3.13.12, scikit-learn 1.6.1, NumPy 2.1.3, pandas 2.2.3, SciPy 1.16.3, joblib 1.6.0. Original Colab metadata retains Python 3.13.16. The audited patch difference is explicit and passed frozen reproduction. The unchanged API environment has different numerical package versions, so it does not deserialize this model. An attempted use of that unverified backend interpreter is rejected. Every worker invocation verifies the four frozen member digests, runtime, pipeline and feature/class order and reproduces all ten frozen records before predicting. No package install/download, retraining, tuning or model replacement occurs.

**Tests executed and outcomes.**

| Check | Result |
| --- | --- |
| Combined new inference, existing Game API, existing preview and original prototype tests | **173 passed**, 5 existing deprecation warnings, 56.85 seconds |
| Additional final invalid-environment configuration guard | **1 passed**, 60 deselected; returns generic no-store 503 |
| Ten frozen labels / thirty class probabilities through the new worker | **10/10 and 30/30 exactly match**, maximum probability difference **0.0** |
| Integrated legacy projection versus historical single-session workbook targets | **18/18 records, 162/162 values match** |
| Strict synthetic Drag & Drop and Hangman through the full protected actual-model route | Both pass; actual classes/probabilities exactly match offline worker outputs |
| Database integrity | Only SELECT statements observed in inference; source-table snapshots and saved heuristic values unchanged |
| Configuration/auth/manifest guards | Disabled, absent/invalid token, export-key reuse (including whitespace normalization), missing/bad manifest pin, invalid code, contract non-acceptance, duplicate/unapproved/excluded/quarantined and mismatched context cases rejected |
| Evidence failure guards | Incomplete session, missing result/outcome, invalid chronology, malformed payload and inconsistent aggregates rejected without model invocation |
| Model/runtime guards | Missing/corrupt model, wrong checksum, dependency/Python mismatch and invalid feature/class order rejected |
| Static validation | Ruff `E9,F` and router whitespace check pass |
| Preservation | Eleven protected artifacts/configuration/source files match their prior byte hashes, including the existing reproduction/evaluation report and model archive |

The 173-test combined run and the final one-case configuration test were separate runs. Neither result is a classifier accuracy estimate. The ten frozen inputs reproduce the original model's behavior, while the eighteen workbook cases compare feature arithmetic only. Complete historical planned-step evidence remains absent from the CSV export; those records were not used as strict full-path genuine fixtures. Full-path records are explicitly synthetic, in-memory SQLite fixtures, not production student data.

The combined regression command, from `backend/`, used `DATABASE_URL=sqlite+pysqlite:///:memory:`, `PYTHONDONTWRITEBYTECODE=1`, a unique test directory under ignored local artifacts and no pytest cache:

```text
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests/test_game_research_inference.py tests/test_game_ml_preview.py tests/test_game_sessions_api.py ../local_ml_artifacts/legacy_adapter_prototype/test_adapter.py --basetemp <fresh-local-test-directory> -q -x
```

**Remaining blockers before live activation:** no real-session approval manifest or dedicated token is configured; a researcher must explicitly approve the legacy contract/scope and exact bindings, including current exclusions. Complete genuine task summaries/event payloads must pass the strict path; CSV reconstruction is insufficient. The live PostgreSQL read-only transaction path and protected hosting have not been exercised here. The original multi-session observation windows and untraceable simulation preparation remain limitations of the existing experimental model; its metadata/status disclose that scope. No evidence establishes calibrated probabilities, verified teacher assessment or live proficiency accuracy.

The protected code can be reviewed and tested while disabled. It does not authorize activation, deploy the model or modify any original research result. No frontend integration is included.
