# M3-A: independent misconception labels and offline Quiz dataset

**Status: engineering foundation only. Taxonomy and assessment form are PROPOSED / PENDING TEACHER APPROVAL. No real teacher labels or learner approvals are supplied here. No ML training is authorized by these files.**

## Verified existing contract

The live Quiz uses concept `linear_equations`, learner codes `STU_` plus 3–6 digits for collection sessions, and session IDs `QUIZ-<UUID>`. Learner codes are caller supplied and can recur across sessions. `quiz_session_id` is unique. The database permits one official first answer per `(quiz_session_id, question_id)`; identical retries reuse it. Later practice tries and revealed feedback stay in browser storage and are absent from the source CSV. Feedback after a first answer can still affect later official answers; the CSV does not record individual feedback exposure.

The read-only export provides `quiz_sessions.csv` and `quiz_responses.csv`. It includes incomplete and post-tutor sessions, so neither file is a ready ML dataset. The session CSV carries `source_session_id`, `quiz_session_id`, `student_id_recorded`, `student_code`, `concept_id`, `learning_cycle_id`, phase, attempt number, status, timestamps and saved-answer count. The response CSV carries `source_response_id`, `quiz_session_id`, `question_id`, `question_code`, question order, concept/subconcept, difficulty, selected option, correctness, response time in **seconds**, confidence (`low`, `medium`, `high`), provisional option `misconception_code`, and timestamps. The provisional codes are `inverse_operation`, `sign_error`, `arithmetic_error`, and `concept_confusion`; blank is also valid. They are **not** independent teacher labels.

The current development bank has ten pre-tutor questions `DEV-PRE-LE-01` through `DEV-PRE-LE-10`: 4 easy, 4 medium, 2 hard, across `one_step_addition`, `one_step_subtraction`, `one_step_multiplication`, `one_step_division`, `two_step_equations`, `variables_both_sides`, and `distributive_equations`. The source JSON says `development_prototype_teacher_review_pending`; its seed sets question and misconception mapping `teacher_validated=False`. Several subconcepts have only one item. This foundation predicts only the broad Simple Equations concept and makes no fine-grained subconcept validity claim.

### Mismatch with new research CSVs

The existing export has **no** independent assessment ID, learner working steps, rater identities, blinded teacher ratings, consensus, consent reference, tutoring chronology, or approval status. The new `02`–`04` CSVs collect those separately. They must never be backfilled from Quiz option tags or deterministic diagnosis. A blank field or a code copied from another learner is a validation failure, not something the pipeline repairs.

## Versioned templates and relationships

| File | Grain and key | Role |
| --- | --- | --- |
| `00_proposed_taxonomy.csv` | One row per category code; version `m3a-taxonomy-v1-proposed` | Proposed definitions, examples, inclusion/exclusion, minimum evidence, overlap, approval reference. `REVIEW` is never a training target. |
| `01_teacher_assessment_items.csv` | One row per item ID; form `m3a-independent-v1-proposed` | Eight different equations with working steps; at least two opportunities each for M1–M4 and multiple M0 opportunities. English prompts are drafts; Sinhala text and accessibility review remain pending. |
| `02_teacher_assessment_sessions.csv` | One row per `assessment_id`; at most one per Quiz session in this initial design | Links the original completed Quiz session and learner code to the independent assessment. Records start/end, tutor status/time, no-hint/no-feedback declaration, assessor blinding, origin, research authorization and coded consent reference. |
| `03_teacher_item_evidence.csv` | One row per `evidence_id` and independent rater/item observation | Preserve a transcription of mathematical working, observed error, provisional category, rater code and verification/quality. Do not enter names or medical details. |
| `04_teacher_consensus_labels.csv` | One row per `label_id` and assessment | Links the same Quiz session/code, form and taxonomy version; records two or more rater codes, evidence IDs, disagreement, adjudication and final verified category. |
| `05_quiz_ml_features.csv` | One completed pre-tutor Quiz session | Generated Quiz-only features. IDs, learner code, concept and completion time are **join metadata**, excluded from `PREDICTOR_COLUMNS`. |
| `06_quiz_ml_labeled_dataset.csv` | One validated Quiz session × independent assessment | Generated candidate joined data; contains a teacher target only after all row-level gates. Never train merely because this file exists. |

The exact columns live in `backend/app/modules/quiz/research_m3/schema.py`; the seven CSV files are parseable schema/templates. Copy templates into an ignored private working directory before adding real research data. Do not put filled learner/teacher CSVs under `research/quiz_m3/`.

### Teacher assessment procedure

1. Obtain ethics/research authorization and a coded consent record in approved storage. Keep the code roster and consent details outside these CSVs. Record only their nonpersonal references.
2. Have Mathematics teachers review the **proposed** taxonomy, examples, exclusions, Sinhala/English wording, answer keys, visual accessibility, item coverage and form. Approval must be real and documented. Change `teacher_review_status` to `approved` only after approval, with a reference to the external approval record. The initial form contains no audio requirement. Give each learner plain text or visual instructions to show every equation step; allow writing or an accessible equivalent. Do not give hints or feedback during this independent assessment.
3. Give the separate assessment **after the completed pre-tutor Quiz and before any AI tutoring**. Record the Quiz session ID exactly, its assigned pseudonymous learner code, form version, timestamps with UTC offset, assessor code, and tutor chronology in `02`. Record `record_origin` as `real`, `synthetic`, `development_test`, or `unverified` truthfully for the **linked Quiz and independent assessment pair**, checking both source histories. `research_authorized=true` and references are necessary but do not prove their authenticity to software.
4. Two teachers should independently review the learner's item working **without seeing Quiz answers, option tags, rule diagnosis or model predictions**. Each teacher records one `03` row per reviewed item, with a unique evidence ID, their rater code, transcribed steps, observed error, proposed M0–M4 or `REVIEW`, and verification/quality. A single arithmetic slip is not enough for a misconception. Preserve the original work in approved research storage; this CSV holds the minimum coded mathematical evidence.
5. In `04`, list rater codes and evidence IDs separated by `|`. Use `agreement` when ratings agree. For disagreement, set `disagreement_flag=true`, use `adjudicated`, record a resolution note, and have an independent reviewer (`verified_by_code`) decide. Unresolved competition or `REVIEW` remains quarantined. M1–M4 require supporting working on at least two distinct items and two raters; M0 requires at least four distinct items. `verification_status=verified` is a teacher decision, never inferred from Quiz option tags.

The blueprint uses different equations from the live ten. M1: I01–I02; M2: I03–I04; M3: I05–I06; M4: I07–I08; M0 is assessed across items. This is **coverage for review**, not evidence of empirical construct validity. Teachers should revise and approve the form before any real administration, with version changes and another validation run if content changes.

## Offline validation and feature extraction

Use an already authorized, local extraction of the Quiz ZIP. The M3-A tool accepts only explicit local CSV paths. It imports no database session, uses no network connection, executes no migration, and does not modify source files. From `backend/` (replace sample paths with actual private paths):

```powershell
.venv/Scripts/python.exe -m scripts.quiz_m3_dataset `
  --quiz-sessions ..\exports\my-quiz-export\quiz_sessions.csv `
  --quiz-responses ..\exports\my-quiz-export\quiz_responses.csv `
  --taxonomy ..\research\quiz_m3\00_proposed_taxonomy.csv `
  --items ..\research\quiz_m3\01_teacher_assessment_items.csv `
  --assessments ..\research\quiz_m3\02_teacher_assessment_sessions.csv `
  --evidence ..\research\quiz_m3\03_teacher_item_evidence.csv `
  --labels ..\research\quiz_m3\04_teacher_consensus_labels.csv `
  --output-dir ..\exports\quiz-m3-run-001
```

The output directory is required, must not already exist, and must be under ignored `exports/` if inside this repository. The tool writes `05_quiz_ml_features.csv`, `06_quiz_ml_labeled_dataset.csv`, `quarantine.csv`, and `quality_report.json`. It never silently overwrites an export. For real work, point `--taxonomy` through `--labels` to approved copies in private storage; the committed templates are pending and empty, so they cannot yield training records.

The feature extractor accepts only **completed pre-tutor** Quiz sessions with ten unique first-answer rows, 4/4/2 difficulty coverage, valid source IDs, matching learner codes and chronology. It summarizes correctness, response times, confidence, high-confidence errors, difficulty performance and provisional selected-option tag counts. IDs and timestamps remain join metadata. No teacher evidence, tutoring outcome, post-tutor answer, deterministic support/mastery score or future assessment field is a predictive feature. Output rows are session units; repeated `STU_` codes must be grouped by learner in any later validation split.

The validator rejects missing/duplicate IDs, code conflicts, wrong form/taxonomy versions, unapproved artifacts, unverified ratings, weak or competing evidence, hints/feedback, tutor chronology violations, missing authorization/consent references, and non-real origins from eligible labels. It records exclusion reasons in `quarantine.csv` and counts in the quality report. It cannot independently authenticate teacher signatures, consent, blinding or protocol fidelity; a human must inspect referenced records. The report intentionally says **NOT TRAINING READY** even if machine checks pass. Class counts and independent learner counts are descriptive; there is no universal minimum sample size in this foundation.

## Research readiness and next milestone

M3-A engineering can be complete while M3-B training remains blocked. Required next work: teacher approval of taxonomy and translated accessible form; authorized real independent assessments before tutoring; retained working-step evidence; blinded independent ratings and resolved consensus; verified consent/protocol records; class coverage review; and a learner-grouped evaluation plan that keeps repeated Quiz sessions from the same learner in one fold. Only then review effective independent learner counts, missingness and class distributions to decide whether supervised training is justified. Do not train or integrate a model as part of M3-A.
