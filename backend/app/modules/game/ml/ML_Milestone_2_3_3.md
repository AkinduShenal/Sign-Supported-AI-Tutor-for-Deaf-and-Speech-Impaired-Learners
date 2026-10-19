# Game ML Milestone 2.3.3 — final teacher assessments and readiness

Preparation only: no model fitting, model serialization, database connection,
migration, deployment, gameplay change or Git mutation.

Final preparation snapshot:
`exports/ml-milestone-2-3-3-20261018-preparation-001/`.
The earlier October 17 preparation snapshot is also retained unchanged.

## Evidence and guarded verification import

Inputs are read directly without extraction or rewriting:

- Original Game export:
  `C:/Users/new user/Downloads/game-collection-2026-10-16T16-29-53-394Z.zip`.
- Edited researcher sheet:
  `exports/ml-milestone-2-3-2-20261017-review-guide-001/session_review_sheet.researcher_copy.csv`.
- Independent assessment evidence actually available locally:
  `C:/Users/new user/Downloads/session_review_sheet.assessment_scores_and_provisional_levels.csv`.
  The filename with `(1)` was not found. The available file contains the matching
  50 session IDs and the three additional assessment columns.
- Frozen October 16 review snapshot and baseline:
  `exports/ml-milestone-2-3-1-20261016-review-001/`.

All 50 IDs are present exactly once in each CSV. Identity, mode, original session
timestamps, completion state and answer counts match the frozen review.
Researcher decisions, bases and notes agree between the two CSVs.

The edited sheet changes 42 protected `existing_verification_status` cells from
`REVIEW REQUIRED` to `genuine gameplay`. Direct import correctly rejects these
edits. A **separate compatible copy** restores only those recognized annotations
from the frozen snapshot and retains the three editable decision columns.
The unchanged `session_verification.import_decisions` then validates that copy
against the original ZIP fingerprint, baseline and all protected fields.
Neither the importer nor its frozen evidence has been weakened or overwritten.
Other protected changes still fail validation. Assessment-column annotations
are interpreted separately and never imported as protected review context.

Imported decisions:

| Decision | Sessions |
|---|---:|
| RESEARCH_VERIFIED | 45 |
| DEVELOPMENT_TEST | 3 |
| EXCLUDED_INVALID_STUDENT_CODE | 2 |
| UNKNOWN | 0 |

The 43 new approvals use the exact basis
`these were done by the students in the school`. This meets the existing
importer's nonblank-basis requirement and is treated as the researcher's explicit
session-by-session assertion. It does not provide independently corroborating
collection logs or prove learner identity from analytics. No evidence is invented.

The two earlier approvals and their full provenance remain unchanged:

- STU_006: `ff5f50f3-5dc3-4aaf-9f45-168ccd92ee2b`.
- STU_007: `e0cb4176-562a-42e3-86d5-eb6fc0b123dc`.

All three exact development exclusions and both STU_0014 exclusions remain.
Both analytics ownership quarantines remain independently recorded:

- `750f7589-ab19-4f95-8772-d1f0af654e2f`: invalid STU_0014 plus quarantine;
  never assigned to STU_014.
- `d16c1dbb-6f14-400f-be97-7f0fe2f535e9`: STU_011 ownership conflict.

Authenticity approval cannot override integrity, incompleteness, missing target
evidence or the unchanged detailed gameplay checks.

## Independently validated assessments

The researcher confirms these are separate teacher-administered mathematics
assessments, not Game scores or Quiz results. Dates are October 15 for STU_001–007
and October 16 for STU_008–016, using Asia/Colombo for comparison. Exact teacher
assessment times are unknown; `assessed_at` remains null.

The separately validated input is `independent_assessments.input.json`.
Each record preserves the original score text, score, source CSV hash and row
numbers, original level and source status, unverified suggestion, confirmed date,
date-confirmation reference and any explicit conflict resolution. The detailed
derivation report is `teacher_score_label_provenance.json`.

| Learner | Teacher score /10 | Assessment date | Used level | Classification source |
|---|---:|---|---|---|
| STU_001 | 3 | 2026-10-15 | Beginner | DOCUMENTED_TEACHER_LEVEL |
| STU_002 | 6 | 2026-10-15 | Intermediate | DOCUMENTED_TEACHER_LEVEL |
| STU_003 | 5 | 2026-10-15 | Intermediate | DOCUMENTED_TEACHER_LEVEL |
| STU_004 | 6 | 2026-10-15 | Intermediate | DOCUMENTED_TEACHER_LEVEL |
| STU_005 | 9 | 2026-10-15 | Advanced | DOCUMENTED_TEACHER_LEVEL |
| STU_006 | 7 | 2026-10-15 | Intermediate | DOCUMENTED_TEACHER_LEVEL |
| STU_007 | 4 | 2026-10-15 | Beginner | DOCUMENTED_TEACHER_LEVEL |
| STU_008 | 5 | 2026-10-16 | Intermediate | TEACHER_SCORE_RUBRIC_DERIVED |
| STU_009 | 7 | 2026-10-16 | Intermediate | DOCUMENTED_TEACHER_LEVEL |
| STU_010 | 6 | 2026-10-16 | Intermediate | DOCUMENTED_TEACHER_LEVEL |
| STU_011 | 7 | 2026-10-16 | Intermediate | TEACHER_SCORE_RUBRIC_DERIVED |
| STU_012 | 8 | 2026-10-16 | Advanced | TEACHER_SCORE_RUBRIC_DERIVED |
| STU_013 | 6 | 2026-10-16 | Intermediate | TEACHER_SCORE_RUBRIC_DERIVED |
| STU_014 | 7 | 2026-10-16 | Intermediate | TEACHER_SCORE_RUBRIC_DERIVED |
| STU_015 | 8 | 2026-10-16 | Advanced | TEACHER_SCORE_RUBRIC_DERIVED |
| STU_016 | 8 | 2026-10-16 | Advanced | TEACHER_SCORE_RUBRIC_DERIVED |

The original CSV reports 10 documented levels and six score-only records.
STU_008 originally reports 5/10 with Beginner. The researcher explicitly clarified
“give intermediet level”. Both original values and the original source status are
preserved, while the used Intermediate label is explicitly rubric-derived. No
teacher-assigned level is fabricated. An unresolved conflict would exclude its
target, and an unreferenced or unnecessary override is rejected.

Thus there are nine consistent documented levels and seven rubric-derived
classifications. The rubric is 0–4 Beginner, 5–7 Intermediate, 8–10 Advanced.
Unverified suggestions are preserved for audit and never supply targets. Original
assessment sheets have not been supplied, so documented-level statuses remain
source claims. The original seven teacher scores are checked against the baseline.

## Timing and actual intervention phase

The whole known gameplay window includes parent and linked event timestamps.
An eligible prospective observation must end on a date strictly before its
independent assessment. Sessions on the same date, or spanning that date, have
unknown assessment ordering. Entirely later sessions are after assessment.
Incomplete sessions show a start-date comparison and remain ineligible.

| Timing category | All 45 candidate sessions | Eligible retrospective sessions |
|---|---:|---:|
| Before assessment | 18 | 8 |
| Same day, ordering unknown | 24 | 20 |
| After assessment | 3 | 1 |

The two previously verified October 15 sessions remain genuine and eligible for
retrospective analysis. Their ordering relative to that day's teacher assessment
is unknown, so they are excluded from prospective evaluation. The new prepared
label timing accurately reflects this; older snapshots remain untouched.

`assessment_phase` is always copied from the recorded Game session. Teacher-test
timing does not imply `post_tutor`. Historical lesson-revision provenance remains
known for the original seven; no revision intervention is inferred for the extra
nine. Their revision fields remain null.

## Paired datasets and readiness

The unchanged audited gameplay aggregation and feature allowlists are reused.
Model A uses first-attempt gameplay score only. Model B uses that same score plus
the existing 12 recorded-behaviour features. Both have identical eligible session
IDs, order and target labels within each analysis purpose. Unverified duration
features remain null. Teacher scores, classifications, dates and source statuses
are audit/target evidence and never predictor features.

The raw candidate cohort has 16 learners, 45 sessions, 31 completed and 14
incomplete. Of the 31 completed candidates, one is integrity-quarantined and
one fails the existing chronology check, leaving 29 eligible sessions.
No synthetic observations or artifacts are read into these cohorts.

| Measure | Retrospective | Prospective |
|---|---:|---:|
| Eligible completed sessions, Model A / B | 29 / 29 | 8 / 8 |
| Independent eligible learners | 16 | 4 |
| Eligible learners with independent targets | 16 / 16 | 4 / 4 |
| Learner classes: Beginner / Intermediate / Advanced | 2 / 10 / 4 | 0 / 3 / 1 |
| Observation classes: Beginner / Intermediate / Advanced | 2 / 20 / 7 | 0 / 7 / 1 |
| Fixed learner-grouped split | Pass | Blocked |
| Overall genuine-data training readiness | Blocked | Blocked |

The existing seed-42 GroupShuffleSplit, 25% learner test fraction, yields 12 train
learners / 22 sessions and four test learners / seven sessions for retrospective
analysis, with no learner overlap and all three classes in both partitions.
Partition observation classes are 1/17/4 train and 1/3/3 test. Multiple sessions
from the same learner are not independent learners. These are mechanical
development checks, not proof of adequate research power.

### Exact remaining evidence blocker

STU_001 session `623ecd5c-da70-45db-abf9-2e91aa7a7486`, Drag & Drop, October 13,
is completed and researcher-verified, but fails the existing chronology check.
For task `LEQ_M_002`, step 0, attempts 3 and 4 both have timestamp
`2026-10-13T05:02:12.148000+00:00`; exported row order places attempt 4 first:

| Attempt | Original source event ID |
|---|---|
| 4 | `42a1adf4-07c9-457f-af02-3974215f5559` |
| 3 | `bd66b3b3-45ef-4ab5-bfc7-69dd7847c6dc` |

This establishes a tied-timestamp ambiguity under the current strict check; it
does not establish that the student actually attempted 4 before 3. No source
reordering, inferred timestamp, guard change or automatic authenticity override
has been applied. Complete original rows from all four tables are retained in
`completed_evidence_failures.json`. The existing rule that a completed, verified
session failing evidence checks blocks training is preserved.

Prospective readiness additionally fails the existing minimum of 20 observations
and six learners (currently eight / four), and has no eligible Beginner learner.
No split seed search or threshold reduction has been performed.

Recommended next step: review the tied-timestamp evidence and agree an explicitly
audited handling policy in a separate task, then regenerate preparation. If the
evidence guard is resolved and a researcher authorizes training, the fixed
retrospective split can support a **preliminary retrospective experiment**. It
cannot establish prospective predictive validity. Prospective work needs more
verified completed gameplay demonstrably before independently timed assessments,
including enough Beginner learners and class coverage in both fixed partitions.
No model training is authorized or performed by this milestone.

## Reproduce preparation only

From the repository's `backend` directory, use PowerShell below. The output path
must be fresh; the final snapshot already exists. The example therefore chooses
`...-002`. Original evidence is never edited. There is no `--train` flag.

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -B -m app.modules.game.ml.assessment_preparation `
  --export "C:\Users\new user\Downloads\game-collection-2026-10-16T16-29-53-394Z.zip" `
  --sheet "..\exports\ml-milestone-2-3-2-20261017-review-guide-001\session_review_sheet.researcher_copy.csv" `
  --assessment-csv "C:\Users\new user\Downloads\session_review_sheet.assessment_scores_and_provisional_levels.csv" `
  --snapshot "..\exports\ml-milestone-2-3-1-20261016-review-001\review_snapshot.json" `
  --baseline "..\exports\ml-milestone-2-3-1-20261016-review-001\review_baseline.json" `
  --score-rubric-resolution "STU_008=Researcher clarification in Milestone 2.3.3: give Intermediate level; preserve original score 5/10 and original Beginner entry." `
  --output "..\exports\ml-milestone-2-3-3-20261018-preparation-002"
```

This single command restores the compatible copy, invokes the existing guarded
verification importer, validates independent teacher evidence, recomputes the
shared integrity/quarantine audit and creates paired preparation outputs for both
analysis purposes. It refuses to overwrite an existing folder. Failure leaves no
complete manifest; do not treat a partial directory as an approved snapshot.

`snapshot_manifest.json` hashes every generated artifact except itself.
`preparation_report.json` records exact source hashes, implementation hashes,
restored protected annotations, preserved approvals, counts, label provenance,
timing, exclusions and grouped evaluation checks. Input hashes are checked again
before completion. These files provide tamper detection and a fresh-folder
convention, not operating-system write protection or a digital signature.

## Validation

Tests cover protected-column restoration, CSV ID/cell validation, independent
score provenance and bounds, explicit conflict resolution, per-learner dates,
unknown assessment times, date/timezone boundaries, incomplete/no-event sessions,
retrospective-only later/same-day observations, retained actual Tutor phases,
quarantine/global guards, identical paired cohorts, target leakage prevention,
no-fit/no-database preparation, immutable output names and manifest hashes.
The preparation and selected regression tests are run with classifier/Pipeline
fitting, joblib saving and psycopg connections patched to fail.
Final result: 219 tests passed; five training/artifact cases were deliberately
deselected. Ruff checks and formatting checks passed for the new modules/tests.
