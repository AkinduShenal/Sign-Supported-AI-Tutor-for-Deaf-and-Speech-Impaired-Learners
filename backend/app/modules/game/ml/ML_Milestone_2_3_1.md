# Game ML Milestone 2.3.1 — bounded integrity quarantine

Preparation only. No model training, database connection, source correction,
deployment or gameplay changes. Source: the unchanged local ZIP
`C:/Users/new user/Downloads/game-collection-2026-10-16T16-29-53-394Z.zip`.

## Source investigation and limits

Both discrepancies already exist in `game_analytics.csv` before ML preparation.
They do not originate in feature extraction or label matching.

| Session | Parent source UUID | Result source UUID | Parent learner | Analytics learner | Answers / events |
|---|---|---|---|---|---:|
| 750f7589-ab19-4f95-8772-d1f0af654e2f | f7219749-86ad-441f-b36f-e88ebc190bb8 | 6a99228f-6846-4e18-9ae9-709f479ca77a | STU_0014 | STU_014 | 20 / 74 |
| d16c1dbb-6f14-400f-be97-7f0fe2f535e9 | 6ff735ba-50dc-43d7-a78c-024ec19d7bfe | 2bba1524-31b4-496f-84c6-1bdf9f84d2c6 | STU_011 | STU_012 | 22 / 75 |

For each pair, `student_id_recorded` and `student_code` disagree. Session ID,
concept, learning cycle and assessment phase agree. All linked exported answers
and events use the parent-recorded identity. Their exact source/client IDs and
unchanged complete CSV rows are retained in the new investigation/quarantine files.
Neither session exists in the earlier October 15 export, so it supplies no earlier
ownership history for these records.

`backend/scripts/export_game_collection.py::export_game_data` writes:

- Parent identity from `GameSession.student_id`.
- Analytics identity directly from `GameResult.student_id`.
- Answer/event identity from the parent session, rather than an independent
  learner field on each original event. Their agreement is not proof of which
  student played.
- `_code` preserves STU-prefixed values; it does not convert STU_0014 to STU_014.

`backend/app/modules/game/service.py::create_game_result` initially copies the
parent identity but returns an existing result unchanged. `models.py::GameResult`
links the session ID with a foreign key; it does not enforce equality between
the result's separate student field and the parent's student field.

The observed raw conflict is consistent with differing stored parent/result
identities under the current exporter. The ultimate write/edit cause, exporter
version used and correct learner cannot be proven from the local ZIP alone.
No production query, update history or original database snapshot was obtained.
External CSV editing also cannot be independently ruled out. No identity is guessed
or reassigned, and no database defect is claimed to have been repaired.

## Why local quarantine is justified

The current snapshot has unique, nonempty parent session IDs and source UUIDs;
unique source result/event IDs; no duplicated client IDs within either event
projection; no orphan links; consistent answer-to-event source/client/session
projections; and manifest counts matching all four tables. Every conflicting
analytics row has one exact parent and one distinct result ID. Quarantine uses
those IDs, never learner-code similarity or dates.

`collection_research.py::audit_collection` now permits local quarantine **only
for analytics learner-ownership conflicts after all shared checks pass**. It does
not downgrade a global error to a warning. The affected session is excluded from
both feature sets, with `QUARANTINED_INTEGRITY` and exact field discrepancies.
STU_0014 retains its stronger primary `EXCLUDED_INVALID_STUDENT_CODE` decision
and also records its integrity quarantine. The other STU_0014 session remains
excluded for its invalid identifier.

Duplicate/missing source identities, duplicate/missing parent UUIDs, orphan rows,
answer/event ownership or projection conflicts, duplicate logical attempts,
multiple result records for one parent and manifest mismatches still block the
whole export. If any such failure exists, local isolation is not confirmed and
no unaffected observations are admitted. Other session evidence checks remain
strict in `prepare_session`; exact authenticity and independent labels are required.

The quarantine contains complete original rows from all four available CSV tables,
plus source hashes. Original ZIPs and earlier outputs remain unchanged. Task-summary
CSV rows and full original event payloads are not present in this export and are
not fabricated. Raw evidence is retained even for excluded or unknown sessions.

## Revalidation and counts

Both previous approvals are preserved and pass all checks against this newer export:

- STU_006: `ff5f50f3-5dc3-4aaf-9f45-168ccd92ee2b`, Drag & Drop, Intermediate.
- STU_007: `e0cb4176-562a-42e3-86d5-eb6fc0b123dc`, Hangman, Beginner.

Their prepared observations are identical to the earlier verified observations.
Both remain pre_tutor with the October 15 after-gameplay/revision assessment
provenance. All seven supplied labels and three development exclusions are intact.

| Measure | Count |
|---|---:|
| Exported sessions | 314 |
| Candidate codes present, STU_001–STU_016 | 16 |
| Candidate sessions / raw completed / other status | 45 / 31 / 14 |
| Explicitly verified genuine learners | 2 |
| Verified completed sessions | 2 |
| Integrity-quarantined sessions | 2 |
| Invalid-code-excluded sessions | 2 |
| Overlap of integrity and invalid-code exclusions | 1 |
| Development exclusions | 3 |
| UNKNOWN candidate sessions in the review sheet | 43 |
| Independently labeled eligible learners | 2 |
| Candidate learners without supplied independent labels | 9 |
| Model A / Model B eligible observations | 2 / 2 |
| Remaining global integrity errors | 0 |

Counts of exclusion reasons overlap; they must not be summed as disjoint groups.
Across the full audit, primary decisions are 306 REVIEW REQUIRED,
2 EXCLUDED_INVALID_STUDENT_CODE, 3 EXCLUDED DEVELOPMENT, 1 QUARANTINED_INTEGRITY
and 2 INCLUDED VERIFIED. The 43 UNKNOWN authenticity decisions include the
integrity-quarantined STU_011 session: authenticity and integrity are separate.
Another 264 sessions are outside the focused review scope and remain unverified.

## Correct expanded review sheet and outputs

Use the newly generated **50-row** sheet:

`exports/ml-milestone-2-3-1-20261016-review-001/session_review_sheet.csv`

It has 43 UNKNOWN, 2 RESEARCH_VERIFIED, 3 DEVELOPMENT_TEST and
2 EXCLUDED_INVALID_STUDENT_CODE rows. Only existing decisions are prefilled;
no new candidate was approved. The previous Milestone 2.3 50-row sheet was
checked against its receipt and was unchanged. Neither that sheet nor the
historical 22-row sheet was imported into this new snapshot.

Preserve the companion `review_snapshot.json` and `review_baseline.json`.
Do not edit the first nine CSV columns or overwrite the original sheet; save an
edited copy for researcher decisions. An older/smaller sheet fails snapshot or
row-completeness checks and must not be combined with the new snapshot.
Authenticity approval cannot override an integrity quarantine or invalid-code
exclusion. Correction of recorded learner ownership requires separate evidence
and authorization outside this milestone.

Preparation output:
`exports/ml-milestone-2-3-1-20261016-preparation-001/`.
It includes the usual audits, paired features, labels, receipts and readiness,
plus `integrity_quarantine.json` and `integrity_investigation.json` with the exact
source/result/event/answer identities and original rows. All outputs are fresh
ignored research artifacts; no prior research file was overwritten.

## Code changes and validation

- `collection_research.py::audit_collection`: bounded analytics-only quarantine,
  explicit global boundary checks, traceable discrepancies and separated counts.
- `collection_research.py::write_outputs`: source-fingerprinted quarantine file
  containing complete original exported evidence.
- `test_game_collection_research.py`: conflicting ownership exclusion, preserved
  evidence/approvals, strict unaffected-session checks, nine shared-corruption
  cases, invalid-code overlap and no exclusion of unrelated STU_014 sessions.
- `test_game_session_verification.py`: preserved UNKNOWN/prior approvals through
  quarantine, and rejection of smaller historical sheets with expanded snapshots.
- Documentation links point to this current report; old milestone results remain
  historical. Session-review importer rules and gameplay/exporter code are unchanged.

172 selected non-fitting checks passed. Model fitting, joblib writes and PostgreSQL
connections were explicitly forbidden during tests. Ruff and whitespace checks
passed. Preparation used `train=False` and created no model artifacts.

## Next researcher decisions

Researcher verification can continue using the new sheet. The remaining 43
candidate-session authenticity decisions need exact collection-log/observation
evidence; approval alone cannot resolve the quarantined session. Independent
assessment labels for STU_008–STU_016 are not supplied and must not be invented.
Investigate both identity discrepancies separately without modifying raw evidence.
Assessment/window compatibility checks also remain unchanged: the existing
collection preparer rejects gameplay after its declared assessment date. The old
October 15 labels are not automatically applied to later sessions, and later dates
do not imply post_tutor.

Real-data training is still **BLOCKED / NOT TRAINED**: only two observations from
two learners, Beginner 1 / Intermediate 1 / Advanced 0, versus the unchanged
20-observation/six-learner guardrails and grouped class-coverage requirements.
Only one of the original seven labeled learners is Advanced, which cannot populate
both learner-separated partitions. No performance or superiority claim is supported.
