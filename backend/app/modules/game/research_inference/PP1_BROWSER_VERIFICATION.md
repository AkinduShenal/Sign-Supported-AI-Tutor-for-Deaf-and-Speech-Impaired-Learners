# Milestone 3.2B — supervised PP1 researcher verification

**Milestone 3.2C private preparation update (2026-10-22):** the ignored root `.env` now holds a newly generated verification key and the verified server-only bearer/model/runtime settings. Experimental inference remains disabled, and no new-session manifest path or pin is configured. The configuration instructions below describe the earlier 3.2B state; do not rerun the old key-generation command. See the local [3.2C readiness and timed test procedure](../../../../../local_ml_artifacts/private_research_setup/PP1_PRIVATE_ACTIVATION_3_2C.md).

**Current behaviour (2026-10-25, agreed by the team): no researcher key.** When `GAME_ML_EXPERIMENTAL_ENABLED=true`, a newly completed session's response carries a one-time receipt, and the browser that completed it sends the receipt automatically to receive that session's prediction. There is no researcher key, confirmation dialog or per-session manifest entry for this browser route. Still enforced: loopback/HTTPS transport and exact `FRONTEND_URL` origin, receipt bound to the exact five-field saved context, five-minute expiry, one successful use, hardcoded exclusions, strict read-only evidence extraction and the frozen worker; a disabled flag or changed model/runtime discards the result. The bearer-only `ml-prediction` route and its manifest are unchanged. The key-based flow described below is historical (the development demo app still uses it).

**Implementation verified with synthetic sessions; normal/private inference remains disabled.** This is a shared researcher-role gate for supervised PP1 work. It does not authenticate individual researchers or learners, establish independent learner identity, or replace the PP2 account/ownership design. It does not validate live proficiency accuracy or change the original mixed real/simulated evaluation.

## Exact flow and approval boundary

1. The normal completion route saves the assessment using the unchanged Game service. Only a transition into `completed`, acknowledged in that response, can receive an additional `research_verification` receipt. An already-completed historical session cannot mint one by repeating completion. Missing/invalid research configuration leaves ordinary completion working and returns no receipt.
2. Receipt issuance requires enabled experimental configuration, the separately configured verification key, and permitted browser transport/origin. Its immutable five-field context comes from the persisted completion response. The random 32-byte receipt is held in browser memory only; the server stores its hash, context, expiry and key fingerprint in a bounded separate in-memory registry. It is not an approval or a credential sufficient to predict.
3. React matches the exact acknowledged session/context to the collection queue and requires both `completed=true` and `Saved`. Only then does the dialog open. Failed/pending saving and responses without a receipt leave the existing Game/save UI intact and the ML card unavailable. The original results-open event and a started session ID are not treated as completion proof.
4. The researcher reviews the displayed code, session ID, concept, learning-cycle UUID and assessment phase, checks the explicit confirmation box, and enters the verification key. The password input is uncontrolled: the key is not React state, configuration, storage or a URL/header. It is submitted once in a JSON body and immediately cleared from the input. The ML service bearer is never sent by the browser.
5. `POST /api/v1/game/sessions/{game_session_id}/research-verification` validates transport/origin, configuration and the submitted key, then explicit confirmation/context, the original SHA-256-pinned manifest policy and the completion receipt. All precede the database dependency. The exact session must already be reviewed and approved in that manifest, with `legacy_contract_accepted=true`. The UI/key does not set that field or create an approval.
6. An exclusive receipt lease prevents concurrent/replayed inference. The route reuses the original read-only `research_database`, `predict_saved_session`, unchanged strict ML preview, legacy adapter and frozen worker. The worker receives only the nine features, with the original checksums, runtime, feature/class order, fixture reproduction and provenance checks.
7. After the slow worker, configuration is re-read, the receipt is checked for expiry/revocation/key rotation, and the original manifest validation/context/pin is checked again. A changed approval or disabled configuration discards the result. A successful receipt is consumed; a controlled failure releases its lease for an appropriate retry within the original window. Predictions are never cached or written to Game/teacher tables.

**Newly completed sessions require a separate reviewed manifest update.** Preserve this restriction: inspect the full saved evidence through authorized research access; prepare a new private manifest version retaining current exclusions/quarantines and approved scope; review the exact five-field entry and explicit legacy acceptance; generate its SHA-256 and configure the new path/pin. Do not overwrite or silently expand the old manifest. The application never writes a manifest. Manifest rejections remain unavailable even with a correct shared key. Current exclusion/development/quarantine decisions must be carried into the reviewed manifest; hardcoded known quarantines/development IDs are additionally always denied by the original gate.

The old STU_016 approval and successful one-time verification do not approve new learners or permit replay through this flow. Historic sessions without a newly issued receipt remain unavailable here. A reviewed manifest does not by itself grant this UI access without the receipt, exact explicit confirmation and shared verification key.

## Endpoints, expiry and throttling

- `POST /api/v1/game/sessions/{id}/complete`: existing save behavior plus optional completion receipt. No receipt on an already completed session, unsupported code/ID, disabled/missing configuration or unsafe transport. The response uses `Cache-Control: no-store`.
- `POST /api/v1/game/sessions/{id}/research-verification`: bounded JSON body containing `researcher_key`, `receipt`, `confirmed: true`, and `context` with `game_session_id`, `student_code`, `concept_id`, `learning_cycle_id`, `assessment_phase`. Returns the original typed `PredictionResponse`, with no secrets or learner identity.
- `POST /api/v1/game/sessions/{id}/research-verification/cancel`: revokes only the matching receipt using its opaque value; returns non-disclosing 204 with no-store. It creates no approval and performs no database lookup. UI cancellation aborts its request and ignores late responses even if cancellation cannot reach the server.
- The original bearer-only `GET /api/v1/game/sessions/{id}/ml-prediction` remains protected and unchanged. No public GET proxy was added.

Receipts expire after **300 seconds**, permit one successful inference, and are limited to **256** active entries (one per exact session). Restart loses them and fails closed. Verification allows **5 failed attempts per direct client address per 60 seconds**, with **20 global failures per 60 seconds**, bounded client bookkeeping, constant-time key comparison and `Retry-After: 60`. Browser-supplied forwarding headers do not select rate-limit identities. Failed submissions are not stored; only timestamps/counts are kept. JSON bodies are limited to 8 KiB, and controlled errors never echo request validation inputs.

This registry and limiter support a **single private backend worker only**. Do not deploy a load-balanced/multi-worker/public instance with this in-memory policy. A shared, reviewed authorization/rate-limit store is separate future work. A lost acknowledgement, expiry, cancellation, restart or successful consumption cannot be reversed by replaying a historical completion; preserve the records and use a new genuinely completed session for this UI workflow. Wrong-key/model failures before consumption can be retried within the window, subject to throttling. This intentionally favors denial over reconstructing or fabricating a browser authorization.

Remote browser use requires HTTPS for both UI and API. HTTP is accepted only for a direct loopback client and loopback API host, never based on forwarded headers. The `Origin` must exactly match the existing `FRONTEND_URL`; origin checking is additional transport/CSRF protection, not identity. Any TLS proxy must be separately configured to supply trusted scheme metadata, strip client forwarding metadata and keep the backend private; deployment settings were not changed here.

## Private configuration (instructions only; not applied)

`ResearchMLSettings` adds `GAME_RESEARCHER_VERIFY_KEY`. Use a new cryptographically generated URL-safe value of at least 32 characters; never a manually invented passphrase. The loader/gate enforces URL-safe length 32–256 and rejects reuse of the ML bearer or CSV key. Random generation is an operator requirement; string validation cannot prove entropy.

For the existing local host runtime, keep these settings in the **ignored repository-root `.env`** read by the existing `ENV_FILE` loader. `ResearchMLSettings` reads it afresh on each request. In particular, do not export the manifest path/pin as fixed process variables if they must be updated after a session completes: process environment takes precedence over dotenv files. This allows a separately reviewed new manifest path/pin to be configured during the receipt window without restarting and losing the receipt. No file is changed automatically.

Required settings:

```text
GAME_ML_EXPERIMENTAL_ENABLED=false
GAME_RESEARCHER_VERIFY_KEY=<new dedicated verification key>
GAME_ML_RESEARCH_TOKEN=<existing distinct server-only ML bearer>
GAME_ML_SESSION_MANIFEST=<absolute path to separately reviewed PP1 manifest>
GAME_ML_MANIFEST_SHA256=<lowercase SHA-256 of exactly those bytes>
GAME_ML_MODEL_ARCHIVE=<absolute trusted frozen ZIP with fixtures>
GAME_ML_PYTHON=<absolute compatible isolated Python executable>
GAME_ML_TIMEOUT_SEC=60
FRONTEND_URL=http://localhost:5173
```

The committed code default remains false; no committed deployment/env example was edited. The normal root env and existing private env were not changed. The old `local_ml_artifacts/private_research_setup/research.env` is only a staging file and is not automatically loaded by the server. After separate authorization, a private operator can privately transfer reviewed settings to the ignored root `.env`, enable only the approved local test, and disable afterward. During a new-session review, configure a new reviewed manifest file and its new checksum in that same dotenv source without restarting. If environment-variable overrides are present, resolve that configuration source before collecting; do not bypass a failed pin or fabricate a replacement receipt. Do not enable a public/production deployment. `FRONTEND_URL` must match the actual browser origin exactly and should be set before server startup; remote origins must use HTTPS. No frontend environment variable contains a key. Container deployment/mounts and distributed workers are outside this local-host implementation and were not configured.

For the existing ignored `local_ml_artifacts/private_research_setup/research.env`, a researcher can generate a new key locally without printing it using the following command from the repository root. This command has **not** been executed by the implementation. It refuses replacement, preserves the disabled flag, and does not approve sessions:

```powershell
@'
from pathlib import Path
from dotenv import dotenv_values
import secrets

path = Path("local_ml_artifacts/private_research_setup/research.env")
values = dotenv_values(path)
if "GAME_RESEARCHER_VERIFY_KEY" in values:
    raise SystemExit("A verification setting already exists; review/rotate it privately.")
if values.get("GAME_ML_EXPERIMENTAL_ENABLED", "false").lower() != "false":
    raise SystemExit("Disable experimental inference before preparing configuration.")
key = secrets.token_urlsafe(48)
assert key not in (values.get("GAME_ML_RESEARCH_TOKEN"), values.get("GAME_COLLECTION_EXPORT_KEY"))
with path.open("a", encoding="utf-8") as output:
    output.write("\nGAME_RESEARCHER_VERIFY_KEY=" + key + "\n")
print("Dedicated key saved privately. Inference remains disabled.")
'@ | backend/.venv/Scripts/python.exe -B -
```

Keep that file private; Git ignore is not encryption. Do not paste either key into chat or logs. Only the verification key is entered transiently by the researcher into the password dialog over approved transport. Do not use the ML bearer there. Disable request-body capture in any proxy/APM; the implementation emits no submitted-key logs and sanitizes errors.

After explicit approval, validate the exact existing manifest schema (`ApprovalManifest.model_validate_json`), hash the reviewed bytes with SHA-256, and set the private pin. Each byte change requires review and a new pin. The schema example deliberately has false legacy acceptance and an empty list; it is not an active approval and must not be automatically promoted. Keep current exclusions and quarantine decisions intact in every reviewed version.

## Frontend behavior

`ResearcherMLResult` replaces only the unavailable-card host; it reuses `MLProficiencyCard` unchanged. The dialog uses native modal focus containment, explicit Escape/Cancel behavior, labelled password/checkbox inputs, disabled duplicate submissions, password clearing, visible error/status feedback and mobile scrolling. It displays the exact acknowledged context. It supports wrong-key retry, bounded cooldown, missing approval, unavailable model, network and malformed-probability states without fake results.

Verification uses a dedicated **75-second** abortable request bound; general Game requests remain at their original timeout. Session-keyed controller cleanup aborts requests and stale responses are ignored. Completion receipts stay outside local/session storage and the durable event queue. Prediction data is component state only. `SHOW_EXPERIMENTAL_LABEL` stays true and presentation-only; hiding it never alters backend provenance, the heading, model values or authorization.

## Files

Created: `browser_gate.py`, `backend/tests/test_game_browser_verification.py`, this document; `frontend/src/game/gameMLVerification.ts`, `ResearcherMLResult.tsx`, `ResearcherMLResult.css`; `frontend/tests/gameMLVerification.test.ts`, `frontend/tests/fixtures/researcherMLVisualHarness.tsx`.

Modified: `access.py` (new private setting), Game `router.py` (additional routes/acknowledgement receipt), frontend `api/gameApi.ts` (memory-only receipt capture), `phaser/PhaserGame.tsx` (controller host), `MLInputDetails.tsx` (two explanatory paragraphs only), `tests/gameMLCard.e2e.mjs` (synthetic modal scenarios), `tests/gameUi.e2e.mjs` (optional synthetic verification after actual mode completion and a safe destroyed-button check). Small documentation links in the prior UI/audit reports identify this explicitly authorized PP1 alternative.

No scene, scoring, task/question bank, event writer, legacy adapter, ML preview, worker, model metadata/weights, teacher label, database schema/migration, shared dependency or deployment configuration was changed. The original creation/completion writes remain the ordinary Game service behavior; verification/cancellation introduce no Game evidence writes.

## Verification and activation status

The implementation was exercised against in-memory synthetic saved sessions, never real learners. The actual frozen model was used for synthetic complete-session endpoint/offline comparisons; this does not establish live student proficiency validity. Runtime/feature/class/checksum/frozen fixture enforcement is inherited unchanged.

Recorded validation runs:

- Backend combined browser-gate, existing inference and strict preview run: **157 passed**. This includes both actual frozen-worker synthetic-session comparisons, one per Game mode. Exact endpoint/offline classes and probabilities matched; each worker reproduced all ten frozen fixtures with maximum probability difference **0.0**.
- Existing Game session API regressions: **29 passed** against isolated SQLite fixtures.
- After adding bounded-store/global-limit coverage and releasing submitted-body references before inference, non-worker gate regression: **72 passed, 2 deselected**. The subsequent separate-reviewed-manifest test: **2 passed** (both modes). These runs overlap the combined run; counts must not be added as independent cases. The final browser-gate file contains 76 parametrized cases, including two real frozen-worker cases.
- Frontend unit tests: **50 passed**, including exact saved-context matching, all three classes, error/malformed/abort handling and no keys in URLs, headers or storage.
- Isolated card browser suite: **48 passed** across all levels, both label settings, loading/unavailable/error, desktop and 390/320px layouts.
- Isolated researcher-dialog browser suite: **36 passed** across saved/pending/failed saves, wrong key, disabled/unapproved/network/malformed/rate-limit states, cancellation and slow-response learner switching. Native dialog accessibility name, initial password focus, keyboard navigation/Escape and 200% text at 320px passed. All responses are explicitly identified synthetic test fixtures.
- Existing actual-Phaser Drag & Drop and Hangman results regression with no receipt: **PASS**, including nine-value JSON clipboard, missing evidence, existing scoring/progression and mobile layouts. No prediction request was made.
- Actual-Phaser Drag & Drop and Hangman positive-verification variant: **PASS**. Each real scene completed through its pointer/keypad controls, the matching mocked save acknowledgement opened the dialog, and confirmation submitted the exact five-field context. Both cards displayed their explicitly labelled synthetic predictions with exact mocked probabilities; passwords were cleared, no key entered browser storage, and no bearer-only prediction GET was made. Existing JSON copy, scoring/progression and 390/320px result layouts passed in the same run. This is browser integration with mocked APIs, not a live PostgreSQL prediction test.
- Frontend TypeScript/production build, targeted Oxlint and backend Ruff `E9,F`: **PASS**. Build retains the existing large-chunk advisory; backend tests retain existing dependency deprecation warnings.
- Final preservation audit checked **25 protected original files**: only the four intentionally changed source files differed from the prior verification baseline. Frozen ZIPs, workbooks, notebook, research evidence, original results, Game service/ML preview and ordinary configuration hashes remained unchanged. Both ordinary and private configurations remain disabled, no verification key is configured, and compiled frontend assets contain neither configured server secrets nor test prediction fixtures.

Reproduction commands (from the relevant `backend/` or `frontend/` directory):

```text
.venv/Scripts/python.exe -B -m pytest tests/test_game_browser_verification.py tests/test_game_research_inference.py tests/test_game_ml_preview.py -q
.venv/Scripts/python.exe -B -m pytest tests/test_game_sessions_api.py -q
npm.cmd test
npm.cmd run build
node tests/gameMLCard.e2e.mjs
```

Use `GAME_RESEARCH_MODAL_TEST=1` for the 36-case dialog browser variant. Use `GAME_ML_PREVIEW_ONLY=1` with `node tests/gameUi.e2e.mjs` for both completed Game modes; additionally set `GAME_RESEARCH_GATE_TEST=1` to exercise the synthetic verification response. These are Node test-runner settings, never Vite or production configuration. Browser scripts start isolated local Vite/Chrome and mock all APIs; the genuine frozen-model checks are separate backend tests.

Visual evidence: [desktop dialog](../../../../../frontend/artifacts/game-ml-card-1792651772880/modal-wrong-1440.png), [320px dialog](../../../../../frontend/artifacts/game-ml-card-1792651772880/modal-disabled-320.png). Full modal evidence: `frontend/artifacts/game-ml-card-1792651772880`; card evidence: `frontend/artifacts/game-ml-card-1792652190222`; original no-receipt two-mode regression: `frontend/artifacts/game-ui-1792651101393`. Artifacts are local/ignored and must not be presented as student predictions.

Final positive two-mode integration evidence: `frontend/artifacts/game-ui-1792653379297/verification.json`; [Drag & Drop mobile synthetic result](../../../../../frontend/artifacts/game-ui-1792653379297/ml-card-verified-fixture-drag-drop-320.png); [Hangman desktop synthetic result](../../../../../frontend/artifacts/game-ui-1792653379297/ml-card-verified-fixture-hangman-1440.png). These screenshots were visually inspected: the test-only banner identifies synthetic values, all three labelled progress bars fit, and the experimental notice remains visible.

**Status: PASS for isolated implementation/security/reproduction checks; PARTIAL for private activation readiness.** No genuine session or browser-to-live-database prediction was tested in this milestone. The earlier STU_016 report is separate historical evidence, not an authorization for this new UI flow.

**Remaining activation blockers:** provision the separate private verification key, explicitly authorize private testing, review each new completed session and its five-field context/legacy scope into a new pinned manifest, configure the compatible isolated runtime and exact browser origin, and use a single private worker with appropriate HTTPS. The five-minute receipt must still be valid after review. No broad session approval or production activation is supplied by this milestone.
