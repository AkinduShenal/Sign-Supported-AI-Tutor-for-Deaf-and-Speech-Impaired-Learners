# Game Question Bank Milestone 2 — v2 Design

Prepared October 20, 2026 (Asia/Colombo). PP1: October 22, 2026.

## Status and scope

**DESIGN ONLY — TEACHER REVIEW REQUIRED — ZERO ACTIVE V2 QUESTIONS.**

This package does not implement a loader, API, migration, seed, release gate or runtime bank. It does not approve questions. No existing question, Game code, scoring, analytics, learner/session record, ML implementation/artifact or other module is changed. No database connection or training is part of this milestone.

The foundation is the **live frontend bank**, not the separate database seed bank. The live bank has 18 questions and 10 distinct original activity IDs. Its provisional reclassification is 7 Beginner / 7 Intermediate / 4 Advanced. The 12 primary additions are 3 / 3 / 6, giving a proposed 30-question roster with 10 per tier. Six reserves (two per tier) remain outside that roster. All counts depend on actual teacher decisions.

## Review package

- [teacher_review_live_v1.csv](teacher_review_live_v1.csv): all 18 original IDs, activities, exact equations/answers, stored and proposed difficulties, reasoning, and blank teacher cells.
- [new_variant_review.csv](new_variant_review.csv): 12 primary additions and six reserves, with blank teacher decisions.
- [TEACHER_REVIEW.md](TEACHER_REVIEW.md): printable tables, reasoning, rubric, replacement rules and special decisions. Print landscape and check print-preview scale.
- [v2_release_manifest.DRAFT.json](v2_release_manifest.DRAFT.json): full proposed question revisions, original provenance, choices, hints, results, null approvals and hashes.
- [DESIGN_VALIDATION.json](DESIGN_VALIDATION.json): engineering checks and protected-source fingerprints. Validation is not educational approval or a research result.

## Rubric requiring teacher approval

Beginner: one inverse operation; judge negative-number demand separately. Intermediate: two inverse operations with the variable on one side; constant denominators may be included. Advanced: variable terms on both sides, multi-step bracket/denominator reasoning, or three or more inverse operations.

The two original multiplicative-bracket questions are provisionally Advanced following the initial bracket guideline, although dividing first gives a two-operation route. A grouped numerator divided by a constant is provisionally Intermediate. This boundary is a specific teacher decision, not an established difficulty fact. Do not classify solely from equation length, parentheses, fractions, or an old activity name.

The old “word problem” questions supply the equation. They do not measure equation construction. Question tiers are not teacher proficiency labels or independent ML targets. Teacher-approved Sinhala instructions/hints remain a separate classroom-readiness dependency; the manifest supplies English draft hints only.

## Eight proposed v2 logical activity revisions

These new groups do not rewrite any original activity ID. They deliberately group the old H003/H004 content as constant-denominator equations.

| Activity revision | Proposed tier | Primary count |
| --- | --- | ---: |
| GQBV2_ACT_ADD_SUB_R01 | Beginner | 5 |
| GQBV2_ACT_MUL_DIV_R01 | Beginner | 5 |
| GQBV2_ACT_TWO_STEP_R01 | Intermediate | 4 |
| GQBV2_ACT_CONSTANT_DENOMINATOR_R01 | Intermediate | 6 |
| GQBV2_ACT_BRACKETS_R01 | Advanced, teacher decision pending | 2 |
| GQBV2_ACT_VARIABLE_BOTH_SIDES_R01 | Advanced | 5 |
| GQBV2_ACT_BRACKETS_WITH_OFFSET_R01 | Advanced | 2 |
| GQBV2_ACT_DENOMINATOR_BOTH_SIDES_R01 | Advanced | 1 |

## Immutable revisions, approval and release manifest

Draft release: `GAME_LEQ_V2_DRAFT_20261020_001`. Candidate rubric: `GAME_LEQ_RUBRIC_V2_001`, currently unapproved.

Question IDs are `GQBV2_Q001_R01` through `GQBV2_Q036_R01`; they do not encode difficulty. Q001–Q018 link to exact original live IDs. Q019–Q030 are primary additions. Q031–Q036 are reserves. All 36 revisions require review; the primary roster has 30, not 36.

Each question records its equation, integer answer, activity revision, superseded v1 ID if any, original activity/difficulty, proposed and approved difficulty, content version 2, rubric version, supported modes, operation choices/results/hints and content hash. `approved_difficulty` and reviewer/date are null; comments are blank. `active_variant_ids` is empty, `activation_enabled` is false, and `production_approved` is false.

A published question revision is immutable. Editing its equation, answer, operation sequence, hint, distractors, proposed tier, rubric or activity mapping requires R02 or another new revision ID. Do not repurpose a legacy ID. A different roster or approval state requires a new release manifest; never overwrite this draft to make it look approved.

Actual teacher approval must be a separate attestation tied to the exact question hash and rubric version, with the actual reviewer and approval date. An approved tier must match the hashed proposal. If the teacher chooses a different tier, issue a new revision and recalculate the roster. The package does not fabricate teacher approval, a review timestamp, or approval evidence.

Hash rules:

1. Canonical JSON: UTF-8, sorted keys, `ensure_ascii=false`, `allow_nan=false`, compact comma/colon separators.
2. A question hash covers all question fields except `content_hash`, `approved_difficulty`, and `teacher_review`. **Proposed difficulty and rubric version are included.** Approval is an attestation, not permission to override a hashed classification.
3. The manifest hash covers the entire manifest except `manifest_hash`, including null approvals and primary/reserve/empty-active lists.
4. Source-file hashes identify the original live-bank snapshot. Checksums provide traceability and tamper detection, not signatures or enforced filesystem immutability.

A future activation gate must require approval of all 30 selected revisions, an approved rubric, correct hashes, 10 approved per tier, unique questions, both-mode/input/language verification and compatible recovery/export evidence. None of that gate is implemented or activated here.

## Compatibility contracts

| Area | Confirmed current source | Future requirement |
| --- | --- | --- |
| Drag & Drop | [EquationGameScene.ts:813](../../../frontend/src/game/phaser/scenes/EquationGameScene.ts#L813), [variantAccess.ts:8](../../../frontend/src/game/data/variantAccess.ts#L8) | Adapt approved steps to existing choices/stepText/resultText/hint. Preserve operation-selection correctness and guided-step evidence. |
| Hangman | [hangmanLogic.ts:17](../../../frontend/src/game/phaser/hangmanLogic.ts#L17), [HangmanGameScene.ts:552](../../../frontend/src/game/phaser/scenes/HangmanGameScene.ts#L552) | Use signed integer answer strings within the current six-character buffer. One final-value unit per question; internal operation steps are not extra Hangman answers. |
| Selection | [variantSelection.ts:4](../../../frontend/src/game/data/variantSelection.ts#L4), [service.py:548](../../../backend/app/modules/game/service.py#L548) | Select six unique questions from one approved release: two per tier. Preserve current exposure/fallback behavior unless separately changed. |
| Completeness | [service.py:247](../../../backend/app/modules/game/service.py#L247), [service.py:349](../../../backend/app/modules/game/service.py#L349) | Keep six tasks and stored 2 easy / 2 medium / 2 hard. Explicitly map Beginner/Intermediate/Advanced to those internal values. |
| Scoring | [service.py:366](../../../backend/app/modules/game/service.py#L366), [research_schema.py:169](../../../backend/app/modules/game/ml/research_schema.py#L169) | Keep stars, persisted analytics and research first-attempt score definitions distinct and unchanged. Drag & Drop uses operation steps; Hangman uses final-value questions. |
| Events/export | [EquationGameScene.ts:846](../../../frontend/src/game/phaser/scenes/EquationGameScene.ts#L846), [HangmanGameScene.ts:599](../../../frontend/src/game/phaser/scenes/HangmanGameScene.ts#L599), [export_game_collection.py:40](../../../backend/scripts/export_game_collection.py#L40) | Keep event names, timestamps, attempt IDs and recorded answers; add pinned release/version/rubric/hash metadata to future evidence. |
| Pending recovery | [pendingGameWrites.ts:3](../../../frontend/src/game/api/pendingGameWrites.ts#L3), [CollectionGate.tsx:122](../../../frontend/src/game/CollectionGate.tsx#L122) | Preserve and recover exact original v1 payloads. Do not clear storage or rebuild pending evidence from the new release. Current Game refresh recovery does not resume unfinished gameplay. |
| ML reproduction | [collection_research.py:402](../../../backend/app/modules/game/ml/collection_research.py#L402), [real_retrospective.py:72](../../../backend/app/modules/game/ml/real_retrospective.py#L72), [synthetic_pp1.py:70](../../../backend/app/modules/game/ml/synthetic_pp1.py#L70) | Preserve frozen catalogs, original IDs/tiers, source files, pinned code, splits and artifacts. Use a separate future v2 preparation adapter. |
| Database | [content_models.py:35](../../../backend/app/modules/game/content_models.py#L35), [seed_equations_game_activities.py:178](../../../backend/scripts/seed_equations_game_activities.py#L178) | Activity owns difficulty. Version fields are not composite revision keys. The current v1 seed accepts exactly 18 BANK IDs, not this draft. |

The current selector permits an over-limit fallback when fewer than two eligible variants remain. Usage counts include persisted attempts across learner/concept sessions without filtering by mode/phase. Preserve that behavior unless separately authorized. New revision IDs start with no usage; a supersedes link does not transfer counts automatically. Do not rewrite historical exposure counts.

Existing result rows are returned without recalculation. Future content can change score and behaviour distributions even when formulas are unchanged. Do not pool releases or compare outcomes without an explicit analysis plan. Historical missing content versions remain unknown; never assign one from calendar date alone.

### Future recording contract

Pin one release before selecting a roster or accepting an answer. A future start event must contain `bank_release_id`, `release_manifest_hash`, `content_version`, `difficulty_rubric_version`, and a six-item `selected_question_roster`: revision/activity IDs, approved internal tier, planned step count and question hash. Bank version is separate from student ID, learning-cycle ID, game session ID and assessment phase.

Retain existing event semantics and add pinned release/version/rubric/question hashes to future question, answer, hint and completion evidence. Record the actual prompt and offered choices, expected/submitted response, original attempt numbers and timestamps. Archive the full release snapshot. Existing event JSON can carry this metadata without an intrinsic migration; task attempts currently have no dedicated content-version field, and an extra request field must not be assumed to persist.

The existing CSV has an answer `content_version` column, but current scenes do not populate it. `game_events.csv` omits full payloads. Future exports therefore need compatible additional fields or a source-linked release/roster member; metadata in event JSON alone is insufficient. Never rewrite historical CSVs or ZIPs.

### Pending writes and release switching

Before enabling v2, implement a tested version-aware queue extension or separate store with coordinated collection locking. Keep `game.collection.pending.v1` intact and preserve the ability to upload v1 records without release metadata. Persist the v2 release/roster/hash snapshot before the first HTTP request. Recover stored payloads with their stable session/event IDs, not payloads regenerated from the current bank. A release switch must never change an open session or its queued evidence. Preserve acknowledgement/completeness checks; closing a collection does not complete an unfinished assessment.

## Database verification still required

The database's actual bank inventory remains unverified; this task does not connect to production. Before shared-DB implementation, obtain an explicitly authorized read-only inventory or supplied export of `game_activity_bank` and `game_activity_variants`: IDs, relationships, statuses, versions and content. Group counts by status and inherited difficulty; check unexpected rows and namespace collisions. Seed definitions do not prove active database contents.

No migration is inherently required for separate revision IDs and JSON release metadata. If later mirrored to content tables, use new activity/variant IDs with a separate additive, release-aware importer; never point relabelled questions at mutable v1 activity rows. Eight proposed v2 activities means eight new revision rows alongside preserved historical rows, not eight total physical rows. Dedicated release foreign keys or version columns would be a separately coordinated schema change. Keep the current v1 seed and its conflict protections intact.

## Implementation sequence after actual teacher approval

1. Validate the completed review sheets offline against the source snapshot: exact IDs/content, complete nonconflicting decisions, allowed tiers and genuine approval references/dates. Blank is pending; rejection is not approval. Review steps, distractors and hints as well as answers.
2. Resolve bracket/sign/language decisions and reserves. Retain all accepted originals; recalculate 30 unique revisions and 10 per approved tier. If both simple brackets become Intermediate, retaining all 18 originals needs additions 3 Beginner / 1 Intermediate / 8 Advanced: swap two primary new Intermediate candidates for approved Advanced reserves Q035/Q036. Do not do this automatically.
3. Issue changed question revisions and a fresh immutable approved release with teacher attestations. Implement new Game-owned release loader/validator files; reject missing approvals, altered hashes, mixed releases, wrong counts and unsupported answers. Preserve the v1 default.
4. Complete database verification. Coordinate any additive importer separately; no database publication or migration is authorized by this milestone.
5. Implement an opt-in local release adapter for both games, preserving existing interaction, stars, scoring, session identity, assessment phase and completeness.
6. Implement pinned session/event/queue/export metadata and backward-compatible recovery before collecting v2 learner evidence. Archive selected release snapshots and retain version-unknown historical handling.
7. Verify arithmetic/choices, positive and negative integer input, teacher-approved language, 10-per-tier bank and six-question 2/2/2 selection, exposure fallback, event/queue retry and idempotency, refresh recovery, completeness and unchanged v1 scoring/behaviour.
8. Verify frozen ML 2.4/2.4.1 inputs and artifacts remain unchanged. Use a separate future release-aware preparation path; do not retrain, activate a model, alter genuine evidence or claim predictive validity from bank changes.
9. Demonstrate locally, then obtain explicit activation authorization. Until these gates pass, v1 stays live and v2 has zero active questions.

## Engineering validation and limits

The package validation uses exact affine/rational arithmetic, independently deriving unique integer solutions and checking every balanced operation, displayed step and simplified result. It checks four distinct choices with one keyed operation per step, input representation, no equation duplicates modulo typography/parentheses/side order, original identities/content, counts, activities, null approvals and canonical hashes. Shared solutions and genuine numerical variants are permitted; formatting-only copies are not.

No application test suite, database fixture, migration, model loader or training runner is executed. The validation report records protected-source fingerprints and check counts. Arithmetic success does not establish teacher approval, browser rendering, classroom suitability or research accuracy. Reproduction runners themselves are not run.
