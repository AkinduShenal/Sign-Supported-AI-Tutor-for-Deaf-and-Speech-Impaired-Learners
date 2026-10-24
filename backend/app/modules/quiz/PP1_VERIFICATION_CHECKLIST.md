# PP1 Dynamic Quiz development verification

Status recorded on 2026-10-22. This checklist concerns the isolated
`tmp/quiz_dynamic_demo.sqlite` database and the 60-item development bank.
It is not a production release or research-data approval.

| Check | Status | Evidence / remaining action |
| --- | --- | --- |
| Bank size and blueprint | PASS | Source JSON and isolated SQLite match: 60 variants, six in each of ten slots, 24 easy / 24 medium / 12 hard. |
| Saved dynamic selection | PASS | Local completed development sessions have ten distinct saved selections, one per slot, yielding 4 easy / 4 medium / 2 hard per session. |
| Answer persistence and result | PASS | Local development session audit confirms ten first answers, response times, confidence, correctness, timestamps, option tags, and a matching stored score. |
| Browser refresh and recovery | PASS — manually reported by project owner on 2026-10-22 | The owner refreshed an active Quiz and verified the selected questions and saved answers were preserved. This is user-reported browser evidence, not an automated browser run in this checklist update. |
| Question content approval for all 60 variants | REPORTED APPROVED on 2026-10-21; evidence pending | Owner reports teacher approval. Bind private approval evidence to the exact bank SHA-256 before final sign-off. |
| Sinhala wording approval | REPORTED APPROVED on 2026-10-21; evidence pending | Record this as a separate scope in the local approval manifest and confirm the private evidence explicitly covers it. |
| Distractor misconception-tag assignment approval | REPORTED APPROVED on 2026-10-21; evidence pending | Record this as a separate scope; check evidence covers option-to-tag assignments. Approval of tag assignment does not automatically validate the broader misconception taxonomy. |
| `teacher_validated` fields | 0/60 dynamic questions; 0/4 misconception mappings true | Leave false in this development version. Current selection filters for false; changing them would break new dynamic sessions. The separate manifest holds reported approval without altering Quiz behavior. |
| Evidence-linked approval record | PENDING | Run `scripts.quiz_dynamic_approval --verify`, then use the prepared manifest. Finalize only after the private evidence reference, evidence hash, reviewed bank hash, and scope are confirmed. |
| Production/shared database | NOT USED | Do not apply a migration, seed, or approval update to Supabase or another shared database from this workflow. |
| Dynamic-compatible ML prediction | PENDING | The existing fixed-question extractor rejects rotating variants. A separate approved dataset, labels, and model are required. |

## Recheck the exact bank before recording evidence

From `backend/`:

```powershell
& .\.venv\Scripts\python.exe -m scripts.quiz_dynamic_approval --verify
```

The current source bank SHA-256 is
`4328557d57e43de791cd00270d8df3746f607a61c6e2ae27c8c9fe66a8e7afad`.
The verifier fails if any of the 60 local question or option values differs
from the source bank. Follow the preparation and finalization commands in
`DYNAMIC_DEMO.md`. Keep original signed evidence in approved private storage.
