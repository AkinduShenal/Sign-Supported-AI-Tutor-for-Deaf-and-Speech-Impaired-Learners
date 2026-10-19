# Game ML Milestone 2.3.4 — attempt chronology and final preparation

Completed October 19, 2026. Preparation only: no real or synthetic models fitted,
no model artifacts saved, no production connection, database writes, migrations,
deployment, gameplay changes or Git mutations.

Final immutable preparation folder:
`exports/ml-milestone-2-3-4-20261019-preparation-001/`.
Start with `READINESS_REPORT.md`, `preparation_report.json` and
`attempt_chronology_audit.json`. Every earlier snapshot is preserved.

## Exact cause and limits of the evidence

Session `623ecd5c-da70-45db-abf9-2e91aa7a7486`, STU_001, Drag & Drop:
task `LEQ_M_002`, step 0, recorded attempts 3 and 4 both have outcome timestamp
`2026-10-13T05:02:12.148000+00:00`. Their matching `ANSWER_SUBMITTED` events also
have that timestamp. The raw records do not resolve their physical timing within
that millisecond.

The exporter explicitly sorts events by session, event timestamp, then event UUID.
Outcome UUID `42a1adf4-07c9-457f-af02-3974215f5559` (attempt 4) sorts before
`bd66b3b3-45ef-4ab5-bfc7-69dd7847c6dc` (attempt 3). The old ML check sorted
by timestamp alone and retained this CSV order for ties. It therefore rejected
the numbered sequence despite there being **no strictly decreasing timestamp**.
This is the exact mechanism of the false chronology inversion.

The inspected recording semantics are:

| Component | Evidence and ordering implications |
|---|---|
| `frontend/src/game/analytics/GameSessionTracker.ts` | `recordAttempt(stepIndex)` synchronously increments one step's `attemptsCount`. `startLevel` preserves an incomplete current level's counts during a rebuild. The counter is independent of timestamps. |
| `EquationGameScene.ts`, `handleOperationSelection` | Reads prior per-step count, increments once, emits `ANSWER_SUBMITTED` followed by the outcome with the same `priorAttempts + 1` and step identity. |
| `HangmanGameScene.ts`, answer submission | Uses the same counter scheme for guess step 0. |
| `frontend/src/game/api/gameBackendSync.ts` | Each event gets `new Date().toISOString()`, with millisecond precision. Multiple calls can have equal timestamps. This is not a monotonic high-resolution sequence. |
| `pendingGameWrites.ts` | Persists an ordered local queue and drains it sequentially. `crypto.randomUUID()` event IDs provide identity/deduplication, not ordering. No queue ordinal is exported. |
| `backend/app/modules/game/models.py`, `GameplayEvent` | Source ID defaults to UUIDv4; stores client event timestamp and payload. `created_at` exists, but is not an exported independent monotonic sequence. |
| `backend/app/modules/game/service.py` | Persists the submitted timestamp and payload. Client-ID retries must match their original evidence. Protocol completion checks positive/contiguous per-step attempt numbers and retry counts; it does not export server receipt order. |
| `backend/scripts/export_game_collection.py` | Writes outcome attempt numbers from event payloads, not inferred CSV positions or task-summary attempt numbers; ordering is `(session, timestamp, UUID)`. |

All five attempts in the affected step have distinct source/client outcome IDs,
one distinct numbered submission each, contiguous numbers 1–5 and a nondecreasing
submission/outcome sequence. There is one hint before attempts 3–5, not tied with
any answer. The shown/completed step boundaries reconcile as well.

The current code and original records support the **recorded logical sequence**
3 before 4 under the per-step counter contract. They do not independently prove
physical order within the millisecond, historical client build, or why two
submissions occurred so close together. Rapid input versus duplicate UI handling
cannot be diagnosed from this export. No timestamp or hidden server order is
invented. The CSV does not contain complete original event payloads or receipt
sequence; matching submissions corroborate the recorded counter, not an external
clock or independently observed human actions.

## Policy evaluation

| Option | Evaluation |
|---|---|
| A — accept ties using an independently recorded monotonic attempt sequence | Selected in a bounded form: use the clock-independent per-step counter only when unique complete submissions corroborate it and all other evidence gates pass. |
| B — retain only demonstrably unaffected features | Unnecessary for this session because every selected score/count feature passes. If required behaviour evidence were ambiguous, keeping the score alone would not justify silently giving Model A and B different cohorts. |
| C — quarantine/exclude the whole session | Appropriate when trustworthy sequence evidence is absent. Such ties remain evidence-blocked and excluded from both models. Existing ownership quarantines remain separate and unchanged. |
| D — retain the training block | Still applies to unresolved completed-session evidence failures and failed sample/class/grouped-split checks. The selected policy does not bypass this guard. Prospective training stays blocked. |

`recorded-attempt-sequence-ties-v1` is checked only after the existing
`game-evidence-v1`, exact approval, identity, source-link and content checks.

1. Outcome attempt numbers must be exactly 1–N, without duplicates or omissions.
2. Timestamps in that numbered sequence must be nondecreasing. A genuine strict
   timestamp inversion remains an error, even when a counter is present.
3. Ties require exactly one numbered `ANSWER_SUBMITTED` event for every outcome
   in the affected step, with matching learner/session ownership and distinct,
   nonempty source and client IDs.
4. Each submission must be no later than its outcome; each outcome must be no
   later than the next numbered submission. Strict contradictions remain errors.
5. Hint/answer ties without independent hint ordering remain blocked. Step shown
   and completed boundaries must also reconcile.
6. Existing answer correctness, first-attempt flags, hint counts, retry counts,
   task roster, ownership quarantine and saved completion checks still apply.

Only derived validation metadata supplies logical ordering. Source arrays are
not sorted in place or rewritten. Metadata preserves original exported outcome
order, original outcome and submission rows, original timestamp strings, tie
groups and `UNRESOLVED_AT_RECORDED_PRECISION` for within-tie wall-clock order.

## Code changes

- `collection_research.py`: adds `audit_attempt_chronology` and replaces the
  timestamp-only stable-sort comparison with the bounded policy above. Sessions
  with unique timestamps retain the existing chronological test. Accepted tie
  decisions are attached to source-link metadata, outside predictor features.
- `assessment_preparation.py`: reuses the existing preparation/import process,
  accepts `--milestone 2.3.4`, and writes a chronology audit with affected
  observations/features. Adds a diagnostic for classes with fewer than two
  independent learners. Sample thresholds, fixed seed, test fraction, teacher
  labels, assessment timing policy and learner grouping are unchanged.
- `test_game_attempt_chronology.py`: invented engineering fixtures exercise the
  policy and its failure paths. No fictional research approvals are added.
- This report and the research README describe the updated readiness.

## Recalculated feature integrity

The recovered observation has 15 recorded answers across 11 planned steps.
The tied attempts are later incorrect attempts; neither becomes a first attempt.

| Audited feature | Recalculated value | Integrity basis |
|---|---:|---|
| First-attempt correct steps | 10 / 11 | Unique recorded attempt 1 for each planned step; source correctness flags independently reconciled with submitted outcome answers. |
| Model A gameplay score | 0.9090909090909091 | Existing first-attempt score extraction, not final success or teacher score. |
| Wrong attempts / wrong attempts per step | 4 / 4÷11 | Four distinct incorrect outcome records, matching the saved summary. |
| Retry count / retries per step | 4 / 4÷11 | Four distinct retry events; equals answers minus planned steps and saved retry total. |
| Hint count / hint usage rate | 4 / 4÷11 | Four distinct hints on four steps; hints-before-attempt reconcile; none shares an answer timestamp in the affected step. |
| Completion rate / task completed | 1 / 1 | All six tasks and all 11 operation steps have reconciled completion evidence and saved completion. |
| Skipped steps / per-step rate | 0 / 0 | Existing full planned/shown/answered/completed roster checks pass. |
| Task duration / duration per step | null / null | Active task timing remains unverified; no elapsed or tied timestamp is substituted. |

These are counts of recorded interactions, not proof of distinct intentional
human mistakes. Different event IDs do not rule out historical UI duplication.
No rescaling, deduplication by guessed intent, outcome correction or response-time
claim is introduced.

The independent target is still Beginner from the teacher's separate 3/10
assessment on October 15. Game heuristic classifications and Quiz results are
never used as targets. `pre_tutor` remains the recorded Game phase.

## Preserved research evidence

All five input files have exactly the same paths and SHA256 hashes as Milestone
2.3.3. All 16 independent assessment inputs and score/label provenance records
are unchanged, including the previously clarified STU_008 Intermediate label.
All 45 genuine approvals, the two earlier approvals, three development exclusions,
two STU_0014 exclusions and both ownership quarantines remain unchanged.

No previously prepared observation or feature value changes. Each new cohort
adds only session `623ecd5c-da70-45db-abf9-2e91aa7a7486`. Both models have exactly
the same session IDs, order and targets within each analysis purpose.

The 45 candidate session timing counts remain 18 before assessment, 24 same-day
ordering unknown and three after assessment. Eligible retrospective timing is
now 9 before, 20 same-day and one after. Same-day and post-assessment sessions
remain excluded from prospective evaluation. No assessment times, Tutor phases
or new revision evidence are inferred.

## Training readiness

| Measure | Retrospective | Prospective |
|---|---:|---:|
| Model A / B eligible observations | 30 / 30 | 9 / 9 |
| Independent eligible learners | 16 | 5 |
| Learner classes: Beginner / Intermediate / Advanced | 2 / 10 / 4 | 1 / 3 / 1 |
| Observation classes: Beginner / Intermediate / Advanced | 3 / 20 / 7 | 1 / 7 / 1 |
| Remaining completed-session evidence failures | 0 | 0 |
| Fixed learner-grouped split | Pass | Blocked |
| Technical training gate | FEASIBLE_PRELIMINARY_ONLY | BLOCKED |

The retrospective fixed split still uses seed 42 and a 25% learner test fraction.
Learner membership is identical to the previous split, with zero overlap:

| Partition | Independent learners | Observations | Observation classes: B / I / A |
|---|---:|---:|---:|
| Train | 12 | 22 | 1 / 17 / 4 |
| Test | 4 | 8 | 2 / 3 / 3 |

The new observation belongs to an existing held-out learner. No seed search,
learner reassignment or threshold reduction occurred. Both partitions contain
all configured classes.

Prospective preparation still fails the unchanged minimum of 20 observations
and six independent learners: it has nine and five. It now has a Beginner
learner, but Beginner and Advanced each have only one learner; neither class can
appear in both learner-disjoint partitions. The all-class partition safeguard
remains enabled. No prospective split or training is forced.

**Preliminary retrospective real-data training is now technically feasible under
the current guards. It has not been performed or authorized by this milestone.**
The next step is researcher review of this policy, immutable snapshot and
retrospective purpose, followed by an explicit request for a separate preliminary
training milestone. Prospective training requires further suitable collection.

## Validation and reproduction

249 selected tests passed; five training/artifact cases were deliberately
deselected. Relevant classifiers/Pipeline fitting, joblib model saving and psycopg
connections were patched to fail during tests and preparation. Ruff lint passed.
New regression coverage includes CSV permutations, valid tied counters, absent
corroboration, strict inversions, missing/duplicate attempts and event identities,
cross-session/learner submissions, hint and step boundary ambiguity, unsupported
recording protocols, first-attempt scoring, quarantine precedence, source
immutability and identical paired cohorts.

Both old and new snapshot manifests were verified. All original input hashes,
prior assessment/verification/quarantine records, existing observations and fixed
learner membership were independently compared and preserved. No model artifacts
exist in the new snapshot. Snapshot manifests detect changes and refuse output
reuse; they are not operating-system write protection or digital signatures.

From `backend`, repeat preparation in a fresh folder (example `...-002`):

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -B -m app.modules.game.ml.assessment_preparation `
  --milestone 2.3.4 `
  --export "C:\Users\new user\Downloads\game-collection-2026-10-16T16-29-53-394Z.zip" `
  --sheet "..\exports\ml-milestone-2-3-2-20261017-review-guide-001\session_review_sheet.researcher_copy.csv" `
  --assessment-csv "C:\Users\new user\Downloads\session_review_sheet.assessment_scores_and_provisional_levels.csv" `
  --snapshot "..\exports\ml-milestone-2-3-1-20261016-review-001\review_snapshot.json" `
  --baseline "..\exports\ml-milestone-2-3-1-20261016-review-001\review_baseline.json" `
  --score-rubric-resolution "STU_008=Researcher clarification in Milestone 2.3.3 on 2026-10-17: give Intermediate level; score 5/10 takes precedence for rubric mapping. Preserve the original Beginner entry and source status." `
  --output "..\exports\ml-milestone-2-3-4-20261019-preparation-002"
```

There is no training flag on this command.

## PP1 limitations

The cohort remains small and imbalanced: only two independent Beginner learners
and four held-out learners total. Repeated sessions do not increase independent
sample size. The passing split demonstrates mechanical feasibility, not research
power, validated generalization, model superiority or deployment readiness.
The retrospective cohort includes same-day and later gameplay relative to teacher
assessment, so its results cannot establish prospective validity. Original teacher
sheets, exact assessment times, historical client/content versions, full original
event payloads, high-resolution/server event sequence and reliable active task
durations are unavailable. Genuine-play assertions are preserved researcher
evidence, not external authentication of every action. Ownership quarantines and
incomplete records remain excluded; synthetic data is not mixed into these sets.
