# Game ML Milestone 2.3 — expanded candidate roster and invalid-code exclusion

Preparation only. No model training, database access, deployment or gameplay changes.

Follow-up: [Milestone 2.3.1](ML_Milestone_2_3_1.md) investigates these source
conflicts, establishes bounded quarantine and revalidates the two approved sessions.
Counts and the global-block behavior below describe the historical 2.3 run.

## Researcher decision

The candidate roster is exactly **STU_001 through STU_016**. Roster membership,
completion and code syntax do not establish genuine participation. Exact manual
session verification and all existing evidence/label checks remain required.

**STU_0014 is an accidental entry, not an alias for STU_014.** Any session whose
`student_code` or original `student_id_recorded` is STU_0014 receives
`EXCLUDED_INVALID_STUDENT_CODE`. It cannot enter either feature set, training or
evaluation even if completed, teacher-labeled or previously approved. The direct
session preparer enforces this exclusion too. No original record is rewritten.

The review sheet includes these records with a protected exclusion decision and
the researcher's correction as its basis. Import rejects attempts to approve,
downgrade or reinterpret that exclusion. An older invalid-code approval is removed
only from the fresh derived review; the baseline and raw export stay untouched.
Valid STU_014 sessions retain the ordinary verification and label requirements.

The exact GAME-SES-2026-001/002/003 development exclusions and other established
manual decisions remain enforced. No date-based exclusions or code normalization
are introduced. Teacher scores for STU_001–STU_007 remain 3, 6, 5, 6, 9, 7, 4.
There are no supplied labels for STU_008–STU_016. Assessment timing after gameplay
and revision remains distinct from actual AI Tutor intervention; phases are unchanged.

## Recalculated local snapshot

Source: `C:/Users/new user/Downloads/game-collection-2026-10-16T16-29-53-394Z.zip`.
Export time: October 16, 2026, 16:29:53 UTC. This is a local read-only snapshot,
not a live database query. Original ZIP hashes and previous outputs are preserved.

| Measure | Count |
|---|---:|
| All exported sessions | 314 |
| Candidate codes present, not confirmed genuine learners | 16 |
| Candidate-roster sessions, excluding STU_0014 | 45 |
| Candidate sessions with raw completed status | 31 |
| Candidate sessions with other status | 14 |
| STU_0014 sessions excluded | 2 |
| Excluded STU_0014 sessions completed / incomplete | 1 / 1 |
| Exact development sessions excluded | 3 |
| Previously approved sessions / learners, approvals preserved | 2 / 2 |
| Independent teacher-labeled learners | 7 |
| Currently evidence-eligible learners / sessions / completed sessions | 0 / 0 / 0 |

The new review sheet has 50 rows: 43 UNKNOWN, 2 RESEARCH_VERIFIED,
3 DEVELOPMENT_TEST and 2 EXCLUDED_INVALID_STUDENT_CODE. The other 264 source
sessions remain outside its focused scope, visible in the complete audit.
Across all 314 sessions: 307 REVIEW REQUIRED, 3 EXCLUDED DEVELOPMENT,
2 EXCLUDED_INVALID_STUDENT_CODE and 2 VERIFIED / EVIDENCE BLOCKED.

### Existing evidence gate blocks this newer export

Two analytics records disagree with their parent session's recorded learner:

| Session | Parent recorded learner | Analytics recorded learner |
|---|---|---|
| 750f7589-ab19-4f95-8772-d1f0af654e2f | STU_0014 | STU_014 |
| d16c1dbb-6f14-400f-be97-7f0fe2f535e9 | STU_011 | STU_012 |

The existing export-wide linkage gate blocks eligible observations on these
mismatches. It has not been weakened, and no records were repaired or reassigned.
The two preserved STU_006/STU_007 authenticity approvals remain approvals, but
this export produces zero eligible observations. Earlier two-observation outputs
remain historical evidence from the earlier snapshot and are not overwritten.
Researcher review of these discrepancies is required before a later preparation
run can be considered ready. Training status is BLOCKED / NOT TRAINED.

## New local outputs

- `exports/ml-milestone-2-3-20261016-review-001/`: editable review sheet, frozen
  baseline, source snapshot and generation summary.
- `exports/ml-milestone-2-3-20261016-preparation-001/`: complete audit, session
  review, preserved assessment provenance, label matching, empty eligible
  observations and paired features, feasibility/status and decision receipt.
- `invalid_student_code_sessions.json` in the preparation directory identifies
  both excluded sessions with their original code, completion and exclusion basis.

Outputs are ignored local research files. Each subsequent generation/import must
use a fresh directory. Regenerate sheets for the new scope; old sheet snapshots
remain tied to their original export and review scope.

To import a completed copy of the new sheet, from `backend/`:

```powershell
.venv/Scripts/python.exe -m app.modules.game.ml.session_verification import `
  --export "C:/Users/new user/Downloads/game-collection-2026-10-16T16-29-53-394Z.zip" `
  --sheet ../exports/ml-milestone-2-3-20261016-review-001/session_review_sheet.csv `
  --snapshot ../exports/ml-milestone-2-3-20261016-review-001/review_snapshot.json `
  --output ../exports/ml-milestone-2-3-preparation-002
```

Do not add `--train`. Unknown decisions require actual researcher review, not
inferred approvals. Additional labels must come from independent assessments.

## Validation

155 selected non-fitting ML tests passed, with model fitting, joblib writes and
PostgreSQL connections explicitly forbidden. Ruff checks passed. Regression
coverage includes completed invalid-code sessions with/without approval, an
edited STU_014 projection retaining the invalid original identity, protected
review exclusions, valid STU_014 handling, expanded unlabeled candidates,
separate completion counts and preservation of source rows.

The preparation run used `train=False`, preserved all seven supplied teacher
scores and both prior session approvals, and created no model artifacts.
