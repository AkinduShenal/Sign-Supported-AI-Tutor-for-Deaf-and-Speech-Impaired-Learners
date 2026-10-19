# Researcher session verification — Milestone 2.2 continuation

Prepared October 16, 2026 (Asia/Colombo). PP1 deadline: October 22, 2026.

## Start here

For the current STU_001–STU_016 candidate roster, protected STU_0014 exclusion,
bounded integrity quarantine and new 50-row review sheet, use
[Milestone 2.3.1](ML_Milestone_2_3_1.md).
The Milestone 2.2 sheet/results below describe the older snapshot. Generate a
fresh sheet for the expanded scope; old snapshots are not interchangeable.

## Historical Milestone 2.2 sheet

Open this local review sheet:

`exports/ml-session-authenticity-20261016-review-001/session_review_sheet.csv`

It has **22 rows: 2 RESEARCH_VERIFIED, 3 DEVELOPMENT_TEST and 17 UNKNOWN**.
It covers the 19 STU_001–STU_007 sessions plus the three exact known development
sessions. The remaining 264 export sessions are outside this focused sheet;
they remain unverified, absent from training and visible in the full source audit.
Across the entire 286-session export there are 2 verified, 3 development and 281 unknown.

The original source is
`C:/Users/new user/Downloads/game-collection-2026-10-15T18-41-34-162Z.zip`.
The previous `session_review.md` and its evidence checks were reused to construct
the existing-verification status; source CSVs supply the exact completion timestamps.

Keep the first nine columns unchanged. Edit only:

| Column | What to enter |
|---|---|
| `researcher_decision` | RESEARCH_VERIFIED, DEVELOPMENT_TEST or UNKNOWN; preserve prefilled EXCLUDED_INVALID_STUDENT_CODE rows |
| `verification_basis` | Collection-log/reference or direct researcher observation that identifies this exact session and learner |
| `review_notes` | Optional context, unresolved issues or additional explanation |

Leave unresolved sessions as **UNKNOWN**. An empty decision is invalid, rather than
an implied approval. Both RESEARCH_VERIFIED and DEVELOPMENT_TEST require a nonblank
verification basis. A high/low score, completion, date, STU-code syntax or common
session-ID prefix is not evidence of authenticity.

For example, a useful basis identifies the collection-log entry, assigned learner,
game mode/device and exact session, checked by the researcher. Do not copy that
example as an assertion unless the supporting evidence actually exists.

The two previously verified sessions and three exact development decisions are
prefilled and protected against downgrading or reversal by this importer.
Any corrections to those established decisions require a separate documented
review; the importer does not silently reinterpret them.

The known development rows have blank `student_code` because that is what the
source export records; their legacy recorded identities are not STU_001–STU_007.
Do not fill in an invented student code. UTC source timestamps remain unchanged;
dates do not classify sessions. When using Excel, import metadata columns as text
so dates and IDs are not reformatted. Save as UTF-8 CSV with the original headers.

You may save the completed sheet as a new filename. Preserve its companion
`review_snapshot.json` and `review_baseline.json`; those are not editable review
inputs. A fresh generated sheet uses a fresh directory and does not overwrite work.

## Import the completed sheet

From the repository root in PowerShell:

```powershell
cd backend
.venv/Scripts/python.exe -m app.modules.game.ml.session_verification import `
  --export "C:/Users/new user/Downloads/game-collection-2026-10-15T18-41-34-162Z.zip" `
  --sheet ../exports/ml-session-authenticity-20261016-review-001/session_review_sheet.csv `
  --snapshot ../exports/ml-session-authenticity-20261016-review-001/review_snapshot.json `
  --output ../exports/ml-session-authenticity-20261016-import-002
```

Change `--sheet` if you saved a completed copy. Choose a new `--output` path for
each import. Import 001 already exists as verification of the unchanged default
sheet; it made no new authenticity decisions. Current work is preparation only;
do not add `--train`.

Before creating output, the importer checks:

- Source ZIP/CSV hashes against the generation snapshot, and the frozen review baseline.
- Every session exists in that export and belongs to this sheet's original scope.
- Exact student code, mode, timestamps, completion, answer count, teacher label
  and prior verification status match the source/baseline.
- No duplicate or conflicting rows; no omitted rows, missing/extra cells or altered headers.
- Allowed decisions, required verification bases and preservation of prior confirmed decisions.

It rejects the entire import on invalid review input. No partial approval is
written. Reordering rows is allowed; removing UNKNOWN rows is not. Missing source
identity/evidence cannot be repaired by editing metadata in the review sheet.
The snapshot detects accidental changes; it is not an authentication service or
independent proof of the researcher's assertions.

All operations are offline. The command imports no database engine/settings,
connects to no database and neither deletes nor updates original source records.
No original export or earlier run is overwritten. It records the reviewed sheet
hash, decision bases/notes, source hashes and updated configuration in the new run.

To generate another sheet from a reviewed baseline:

```powershell
.venv/Scripts/python.exe -m app.modules.game.ml.session_verification generate `
  --export "C:/Users/new user/Downloads/game-collection-2026-10-15T18-41-34-162Z.zip" `
  --review ../exports/ml-session-authenticity-20261016-import-001/review_input.json `
  --output ../exports/ml-session-authenticity-review-002
```

Use the latest imported `review_input.json` to carry forward verified and exact
development decisions. A changed source export requires a new sheet/snapshot;
never pair an old sheet with a different export.

## What happens after import

Only RESEARCH_VERIFIED sessions proceed to the existing Milestone 2.2 evidence
checks. An approval confirms authenticity; it does not establish completeness or
metric reliability. An authentic unfinished session remains separate with a
VERIFIED / EVIDENCE BLOCKED reason and cannot enter the training observations.
All UNKNOWN sessions remain outside training. DEVELOPMENT_TEST applies to that
exact ID only, without modifying source data or excluding neighbouring IDs/dates.

The imported configuration adds optional exact `development_sessions` references
to the existing collection-review contract. Existing review files still load with
an empty mapping. Conflicting verified/development configurations are rejected.
The original three hard-coded development IDs remain mandatory exclusions.

The existing audit reconciles sources, learner/session/concept/phase, variant and
step rosters, attempts, correctness, hints, retries and completion summaries.
Drag & Drop scores operation steps; Hangman scores final-value guesses. Both
paired feature sets reuse the same eligible observations, labels and learner groups.
Missing active timing remains null. Teacher assessment score/level and Game
heuristic classifications remain outside predictor selection.

Teacher provenance remains October 15, date-only, after gameplay and short lesson
revision; no timestamp is invented and no phase is relabelled post_tutor.
Teacher-assessed proficiency remains represented by the existing mastery-label slot.

Each import produces the existing cleaned observations, feature files, source links,
label matching, feasibility/status reports and full session review, plus:

- `researcher_decisions.json`: imported decisions, bases/notes and provenance hashes.
- `incomplete_sessions.json`: all source sessions without saved assessment completion,
  including authentic incomplete sessions and their reasons.
- `unknown_sessions.json`: all unverified source sessions, including those outside
  the focused review sheet.

The existing Milestone 1.1 grouped split, train-only preprocessing and paired
classifier code are unchanged. `--training-config` optionally takes its existing
ExperimentConfig JSON, including classifier choice (Logistic Regression, Decision
Tree or Random Forest). The collection workflow requires the proficiency rubric
class order, mastery target and empty common context to preserve a pure score-only
baseline. It does not search seeds or relax validation guardrails automatically.

If all gates pass, `--train` saves PRELIMINARY/EXPERIMENTAL Model A and Model B
artifacts and checks reload plus label-free offline inference. Predictions on
training/input observations are engineering checks, not independent evaluation.
If gates fail, preparation still succeeds with explicit BLOCKED/NOT TRAINED reports
and no model files. No result is integrated into gameplay.

## Current result and PP1 blocker

The untouched-sheet import is
`exports/ml-session-authenticity-20261016-import-001/`.
It includes only these existing verified learner/session units:

| Learner | Exact session | Mode | Teacher label | First-attempt score |
|---|---|---|---|---:|
| STU_006 | ff5f50f3-5dc3-4aaf-9f45-168ccd92ee2b | drag_drop | intermediate | 5/10 = 0.50 |
| STU_007 | e0cb4176-562a-42e3-86d5-eb6fc0b123dc | hangman | beginner | 3/6 = 0.50 |

There are two observations from two independent learners. Both feature sets have
that same cohort. Distribution: **beginner 1, intermediate 1, advanced 0**.
Model A and Model B were **not trained**; no real model artifacts or real offline
inference results exist. Preparation reports the missing Advanced class and the
unchanged 20-observation/six-learner guardrails. Even lowering sample guardrails
would not create a valid train/test split from one learner per observed class.

Completing the sheet is the immediate PP1 dependency. Authenticity cannot be
inferred by the software. In addition, only one of the seven teacher-assessed
learners is Advanced: meaningful three-class grouped cross-validation or all-class
coverage in both partitions needs additional independently labelled learners.
Historical content versions, exported task summaries and reliable timing remain
missing evidence, as recorded in the original Milestone 2.2 report. A seven-learner
pilot cannot demonstrate reliable generalization or superiority of Model B.

## Engineering verification

Actual result: **221 tests passed** in 18.70 seconds, including 24 new review
workflow cases and the 197 existing relevant ML/Game/export checks. One existing
Starlette/httpx deprecation warning remains. Ruff and `git diff --check` passed.
Final assertions confirmed the original ZIP checksum and the two previous cleaned
observations were unchanged. The untouched-sheet import preserved 273 sessions
without saved assessment completion separately and 281 unknown sessions across
the full export. No real model artifacts or real inference results were created.

New tests use synthetic source records and invented review decisions only. They
cover preserved defaults, exact additional exclusions, explicit approvals, source
context changes, duplicate/conflicting decisions, unknown decisions, missing bases,
source/baseline changes, omissions, incomplete-session isolation and no overwrite.
Existing ML/artifact/metric/Game API/export regressions remain part of validation.

From `backend/`:

```powershell
$env:DATABASE_URL = 'sqlite+pysqlite:///:memory:'
.venv/Scripts/python.exe -m pytest tests/test_game_session_verification.py tests/test_game_collection_research.py tests/test_game_research_ml.py tests/test_game_ml.py tests/test_game_sessions_api.py tests/test_game_collection_download.py tests/test_game_export_cli.py -q -p no:cacheprovider --basetemp=../tmp/game-session-verification-tests-002
.venv/Scripts/python.exe -m ruff check app/modules/game/ml tests/test_game_session_verification.py tests/test_game_collection_research.py --no-cache
```

Files added: `session_verification.py`, this guide and
`backend/tests/test_game_session_verification.py`. Compatible additions to
`collection_research.py` preserve exact researcher development decisions and reject
contradictory configurations. The ML milestone/README link this continuation.
All real review sheets, decision inputs and prepared datasets remain under the
already ignored root `exports/` directory. Existing uncommitted work is preserved;
no database, migrations, gameplay, other modules, commits or branches are changed.
