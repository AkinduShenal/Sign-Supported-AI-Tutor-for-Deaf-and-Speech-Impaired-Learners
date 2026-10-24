# Dynamic Quiz ML feature contract (engineering v1)

`dynamic_ml_features.py` is a read-only extractor. It accepts only a completed
`pre_tutor` linear-equations session on bank `pp1_dynamic_v1_DRAFT`. Its output
identifies `quiz_dynamic_features_v1` and contains 62 ordered numeric predictors.
It is **not** an ML prediction, a teacher label, or a research-validated score.
The existing fixed-question extractor and M3-A offline pipeline remain separate.

**2026-10-22 development update:** A synthetic-trained Colab artifact is now
connected behind two default-off flags and the exact isolated demo SQLite path.
See `DYNAMIC_DEMO.md` for the running procedure. The research integration
described below remains future work; no genuine teacher-labelled model or
prediction-storage migration has been added.

## Data lineage and gates

One row represents one completed Quiz session. The session supplies the student
code, bank version, phase, status and completion time. `quiz_session_questions`
supplies the immutable ten-question order. `quiz_questions` supplies variant code,
logical slot, skill and difficulty. `quiz_responses` supplies the one saved
official first answer per selected question, correctness, response time (seconds),
confidence, provisional misconception tag, order and timestamp.
`quiz_question_options` independently checks that each selected option belongs
to its question and that saved correctness and tag match the option.

The extractor rejects missing/extra/duplicate answers, selection or order
mismatches, missing timestamps, invalid times/confidence, invalid options,
unsupported bank/phase/concept, and any question that does not match the pinned
slot/skill/difficulty blueprint. It does not read practice retries, QuizResult
rule diagnoses, post-tutor data, teacher labels or model outputs. Zero-valued
conditional means (`correct_time_mean_sec`, `incorrect_time_mean_sec`, and the
two conditional confidence means) mean there were **no observations** in that
group; the matching correct/incorrect count disambiguates this. The 4/4/2
difficulty counts and ten slot counts are fixed by the pinned blueprint.

## Predictor columns

The exact **ordered** names are `FEATURE_NAMES` in `dynamic_ml_features.py`.
All are calculated from the saved first answers:

- Total: `correct_count`, `incorrect_count`, `accuracy`.
- Difficulty: for each `easy`, `medium`, `hard`, `<tier>_correct_count` and
  `<tier>_accuracy`.
- Logical slot: `slot_S01_correct` through `slot_S10_correct`, each 0 or 1.
- Mathematical skill: `skill_<name>_correct_count` and `skill_<name>_accuracy`
  for `one_step_addition`, `one_step_subtraction`, `one_step_multiplication`,
  `one_step_division`, `two_step_equations`, `variables_both_sides`, and
  `distributive_equations`.
- Time: `response_time_mean_sec`, `response_time_median_sec`,
  `response_time_min_sec`, `response_time_max_sec`, `response_time_std_sec`,
  `correct_time_mean_sec`, `incorrect_time_mean_sec`,
  `first_half_time_mean_sec`, `second_half_time_mean_sec`.
- Confidence: `confidence_low_count`, `confidence_medium_count`,
  `confidence_high_count`, `confidence_mean` (low=1, medium=2, high=3),
  `high_confidence_wrong_count`, `low_confidence_correct_count`,
  `confidence_correct_mean`, `confidence_incorrect_mean`.
- Distractor evidence: `option_inverse_operation_count`,
  `option_sign_error_count`, `option_arithmetic_error_count`,
  `option_concept_confusion_count`, `repeated_tag_type_count` (tag types seen
  at least twice), `repeated_tag_error_count` (all errors bearing such tags),
  `max_same_tag_count`.
- Sequence in saved question order: `max_wrong_streak`,
  `first_half_correct_count`, `second_half_correct_count`,
  `correctness_switch_count`, `wrong_after_correct_count`.

No raw question or option IDs, option letters, student codes, timestamps, or
answer text enter the predictors. Variant-independent slots and option *meaning*
are used instead. The four option tags are provisional distractor descriptions;
they must never be copied into teacher labels. Editing question skill, tier or
tag semantics requires a new bank version and a reviewed feature schema.

## Isolated development inspection

From `backend/`, with the demo SQLite file already present:

```powershell
& .\.venv\Scripts\python.exe -m scripts.inspect_dynamic_features_dev `
  --session-id QUIZ-8b975912-dea7-4e4f-a8c0-026d2428f67c
```

This command hardcodes `../tmp/quiz_dynamic_demo.sqlite`, opens it in SQLite
read-only mode, and prints JSON. It does not load application database settings.
The JSON metadata fields (`quiz_session_id`, `student_code`, `bank_version`,
`quiz_completed_at`, `feature_schema_version`, `feature_names`) are provenance
and model compatibility checks, not predictor values.

## Training dataset contract for Colab

Create a **private**, coded, one-row-per-session dataset after independent
teacher assessments exist. Keep genuine, synthetic and development records in
separate files. The empty
`research/quiz_m3/07_dynamic_labeled_dataset_TEMPLATE.csv` has the exact
ordered 75-column header. Use these columns:

`quiz_session_id, student_code, bank_version, feature_schema_version,
quiz_completed_at, assessment_id, label_id, taxonomy_version, form_version,
teacher_category, record_origin, verification_status, research_authorized,
<FEATURE_NAMES in exact order>`.

The join key is `quiz_session_id`; check the student code and chronology against
the independent assessment. Only a real, authorized, independently verified
teacher consensus category may be a training target. `REVIEW` and unresolved
assessments are excluded. IDs, dates, origin, verification and authorization
are audit/split metadata, never predictors. Preserve a separate provenance
record for rater evidence and consent references. Decide with teachers whether
the task is single-label M0–M4 or multilabel before fitting; the current
proposed consensus template is single-label. M0 matters so a model need not
force every learner into M1–M4.

In Colab, first load the private CSV and assert exact schema/bank/taxonomy
versions, ordered predictor names, finite numbers, unique session IDs and
verified real labels. Group splits by `student_code`. Fit preprocessing **only
on training folds**. Compare three nested predictor sets using the same folds:

1. Score-only: `correct_count` (and optionally its equivalent `accuracy`).
2. Behaviour-aware: all predictors except the `option_*` and repeated-tag
   features. Report an ablation with/without slot and skill features if the
   genuine sample is small.
3. Misconception-aware: the full 62-feature vector, including provisional
   distractor evidence.

Use a regularized, interpretable baseline such as multinomial logistic
regression; compare more complex models only if independent learner counts
support it. Report per-class support, confusion matrix, macro F1, class recall,
calibration and uncertainty across learner-grouped folds. Select and freeze the
winning pipeline on training data, then evaluate once on a held-out learner
group. Avoid reporting a performance claim from development sessions or
synthetic rows. Keep the old Colab fixed-question artifact untouched.

## Later backend integration

After a compatible trained and tested artifact exists, export the **whole**
preprocessing-plus-model pipeline and a manifest containing artifact checksum,
model version, bank version, ordered feature names, feature schema version,
taxonomy version, training origin/counts, evaluation summary and validation
status. Backend inference should load only a matching manifest, extract from
the completed saved session, and return M0–M4 probabilities/status with the
versions. A missing/incompatible/failed model should record a nonblocking
prediction status and leave Quiz completion, Score, Correct and Incorrect
unchanged. Persist predictions in a new versioned table (or reviewed equivalent)
through a new Alembic migration after schema review; never apply it remotely
without explicit approval. The result page should render actual model output
only when such an artifact is available, and mark unvalidated output
**experimental**. No teacher label is needed during inference.

## Current training blockers

The local `research/quiz_m3/03_teacher_item_evidence.csv` and
`04_teacher_consensus_labels.csv` contain headers only. Taxonomy
`m3a-taxonomy-v1-proposed` and independent assessment form
`m3a-independent-v1-proposed` remain pending. Reported approval of the 60 Quiz
questions, Sinhala text and option tags does not verify independent **student**
M1–M4 labels or approval of those taxonomy definitions. M2 balancing has no
corresponding option tag; M4 coefficient/division is not the same as the broad
`arithmetic_error` tag. Actual teachers must reconcile these definitions and
the assessment form before a supervised training target is declared.

Additional collection limits to record in any study: the Quiz stores selected
options but not a learner's mathematical working steps, and it does not save a
per-question record of feedback exposure or later practice retries. Feedback
after an official first answer can influence later first answers. Development
SQLite timestamps are stored without an explicit UTC offset; retain an explicit
timezone convention in future exports. None of these missing fields should be
invented or backfilled from option tags.
