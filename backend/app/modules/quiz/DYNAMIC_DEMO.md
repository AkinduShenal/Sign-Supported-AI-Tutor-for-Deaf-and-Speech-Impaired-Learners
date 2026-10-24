# PP1 dynamic Quiz development demo

The 60-item bank in `scripts/quiz_dynamic_60_DRAFT.json` follows the existing
ten Quiz skills and 4/4/2 difficulty blueprint. The original ten items remain
the default bank. On 2026-10-22 the project owner reported that a teacher
approved all 60 question variants, their Sinhala wording, and their distractor
tags on 2026-10-21. The approval evidence will be supplied later, so this is
a reported approval, not yet an evidence-linked sign-off or research-use gate.
Dynamic mode remains for isolated development only. See
`PP1_VERIFICATION_CHECKLIST.md` for the current verification status.

## Local database setup (PowerShell)

From `backend/`:

```powershell
& .\.venv\Scripts\python.exe -m scripts.prepare_quiz_dynamic_demo
```

This creates `../tmp/quiz_dynamic_demo.sqlite` only if the file does not exist.
It seeds ten fixed and 60 draft questions. It never reads `.env` or connects to
Supabase. To validate and import the bank into another **already migrated local**
SQLite database:

```powershell
& .\.venv\Scripts\python.exe -m scripts.seed_quiz_dynamic --database-url sqlite:///../tmp/quiz_dynamic_demo.sqlite
& .\.venv\Scripts\python.exe -m scripts.seed_quiz_dynamic --database-url sqlite:///../tmp/quiz_dynamic_demo.sqlite --apply
```

The first command is a dry run. The second is idempotent and refuses to
overwrite different existing content. It rejects remote database URLs.

## Run two sessions

In a backend PowerShell window, from `backend/`:

```powershell
$env:DATABASE_URL = 'sqlite:///../tmp/quiz_dynamic_demo.sqlite'
$env:QUIZ_DYNAMIC_DEV_ENABLED = 'true'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

In a frontend PowerShell window, from `frontend/`:

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
$env:VITE_QUIZ_DYNAMIC_DEV = 'true'
npm.cmd run dev
```

Open `http://localhost:5173`, choose Quiz Assessment, enter an assigned-style
demo code such as `STU_001`, and complete the first session. End collection,
then enter `STU_002` and start another. Each session has one saved variant per
slot. Refreshing a session retrieves its saved selection. The project owner
manually verified browser refresh and recovery on 2026-10-22 and reported PASS.
Random selection allows two sessions to coincide by chance; the tests force
different choices to prove the selection path can differ.

Turn off both feature flags to return to the fixed Quiz. Existing unfinished
fixed collections in the same browser profile still use their saved fixed plan.
Keep the same browser profile until pending writes are saved.

## Record exact-version teacher approval locally

The isolated demo database and source JSON currently contain 60 matching draft
items. All 60 `quiz_questions.teacher_validated` flags and the four
`misconception_mappings.teacher_validated` flags are still false. **Do not flip
them:** current dynamic selection samples only questions with
`teacher_validated=false`. Approval evidence is recorded separately, without
changing selection, scoring, sessions, or the database.

From `backend/`, inspect the source bank against the isolated SQLite file:

```powershell
& .\.venv\Scripts\python.exe -m scripts.quiz_dynamic_approval --verify
```

The script reads only `../tmp/quiz_dynamic_demo.sqlite` in SQLite read-only
mode and checks all 60 question and option values against the source JSON. It
prints the SHA-256 of the exact bank file. Prepare a local manifest recording
the owner-reported approval date and three separately reported scopes:

```powershell
& .\.venv\Scripts\python.exe -m scripts.quiz_dynamic_approval --prepare `
  --approval-date 2026-10-21 `
  --reported-scopes question_content sinhala_wording distractor_tags
```

This creates `../tmp/quiz_dynamic_approval_pending.json` without overwriting
an existing manifest. It fingerprints each variant's question content, Sinhala
wording, and option-to-misconception tag assignments separately. It records a
**user report pending evidence**, not an authenticated teacher sign-off.
Keep the teacher's signed or otherwise verifiable source evidence in approved
private storage, outside the repository. The evidence must identify this exact
bank SHA-256 and explicitly confirm each scope being recorded. The blank lines
in `scripts/quiz_dynamic_60_teacher_review.md` are a review template, not
approval evidence.

After the evidence is available and its scope and bank hash have been checked
by a person, compute its SHA-256 locally (`Get-FileHash -Algorithm SHA256`) and
create an immutable evidence-linked development record:

```powershell
& .\.venv\Scripts\python.exe -m scripts.quiz_dynamic_approval --finalize `
  --approved-scopes question_content sinhala_wording distractor_tags `
  --evidence-ref '<private evidence reference>' `
  --evidence-sha256 '<64-character evidence file SHA-256>' `
  --reviewed-bank-sha256 '<bank SHA-256 printed by --verify>'
```

The final record is created only once at
`../tmp/quiz_dynamic_approval_record.json`; it contains evidence references and
hashes, not the private evidence file or teacher name. `--finalize` refuses a
bank mismatch. Human review is still needed to authenticate the evidence. The
manifest does not alter `teacher_validated`, approve research deployment, or
make the original fixed-question ML model compatible with dynamic sessions.
Both manifests are in ignored local `tmp/`; preserve a copy of the final record
with the private approval evidence so the hash-linked audit trail is not lost.

## Migration and database review

`20261021_0008_add_dynamic_quiz_selection.py` adds nullable `bank_version`
and `logical_slot` to `quiz_questions`, nullable `bank_version` to
`quiz_sessions`, and the `quiz_session_questions` join table. Historical rows
are unchanged. The Alembic chain does **not** create the existing Quiz content
and session tables; verify those tables and their constraints on the actual
target before approving a migration. The migration was tested on a simulated
legacy SQLite schema with a preserved question row. The local demo bootstrap
uses ORM `create_all`, so it does not apply the migration to a shared database.

Before any shared or production migration, approve the exact target database,
a schema/constraint comparison, backup and rollback plan, a PostgreSQL staging
rehearsal, and a separate review of authenticated teacher evidence and the
specific question, Sinhala, and distractor-tag scopes.
Do not seed the drafts into research collection.

The experimental 45-feature fixed Quiz ML output is hidden for dynamic
sessions; its training mapping is incompatible with rotating variants.

## Experimental Dynamic Quiz ML prediction (isolated development only)

Place the Colab-exported `quiz_dynamic_62_SYNTHETIC_DEMO.joblib` and
`quiz_dynamic_62_SYNTHETIC_DEMO_manifest.json` together in the ignored
`../local_ml_artifacts/quiz_dynamic_62_demo/` directory. The backend verifies
the manifest, SHA-256, 62-feature order, bank and schema versions, four output
labels, synthetic training origin, and 0.50 thresholds before deserializing
the local model. It reads first answers from the saved completed session; the
browser cannot submit feature values for prediction. The endpoint is available
only when both backend flags are enabled **and** the connected database is the
exact `../tmp/quiz_dynamic_demo.sqlite` file. No migration or prediction table
is involved.

Start the backend from `backend/` in a new PowerShell window:

```powershell
$env:DATABASE_URL = 'sqlite:///../tmp/quiz_dynamic_demo.sqlite'
$env:QUIZ_DYNAMIC_DEV_ENABLED = 'true'
$env:QUIZ_DYNAMIC_ML_DEMO_ENABLED = 'true'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Start the frontend from `frontend/` in a second window:

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
$env:VITE_QUIZ_DYNAMIC_DEV = 'true'
npm.cmd run dev
```

Open `http://localhost:5173`, start the Dynamic Quiz with a new development
code, submit all ten first answers, and finish recording. On the results page,
Score, Correct and Incorrect appear first. The experimental block underneath
shows the actual model's four independent M1–M4 probabilities and 0.50 flags,
with the prominent synthetic-training disclaimer. Refreshing the completed
session retrieves the saved answers and repeats inference from the same
session. Missing or incompatible artifacts show **Prediction Unavailable**
without changing Quiz completion or score. The fixed Quiz does not call this
dynamic endpoint.
The prediction request allows 60 seconds for the first local model load. If
prediction is unavailable, the result shows the request or artifact reason and
a **Try prediction again** button; quiz completion and score stay saved.
The backend `QUIZ_DYNAMIC_ML_DEMO_ENABLED` flag is the prediction gate; the
frontend does not require a separate ML flag. The backend also requires the
exact isolated SQLite development database before it returns predictions.

For the completed STU_035 development session, a read-only endpoint check is:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/quiz/sessions/QUIZ-e30e7874-52ce-4ee4-a965-dce613f7e010/experimental-prediction'
```

The Colab reference rounds to M1 25.72%, M2 5.77%, M3 74.49%, M4 99.69%.
These are regression reference values, never hardcoded responses. The local
backend currently uses scikit-learn 1.7.2 while the artifact was exported
under 1.6.1; loading emits compatibility warnings. The saved-session outputs
were checked against the Colab reference, but matching dependency versions is
preferable for a later release. The model is trained only on simulated data;
none of these percentages are independently teacher-confirmed diagnoses.
