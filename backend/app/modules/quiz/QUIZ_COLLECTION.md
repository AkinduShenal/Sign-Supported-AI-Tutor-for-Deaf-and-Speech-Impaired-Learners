# Quiz research collection

The Quiz researcher gate requires an assigned `STU_` code followed by 3–6 digits. A client-idempotent Quiz session carries that code in `quiz_sessions.student_id`. Its queued answers are written to `quiz_responses`. The queue is stored under `quiz.collection.pending.v1` in the browser profile and origin used for collection. Keep that profile until all pending writes show **Saved**. **Assessment Complete** appears only after the backend accepts all 10 configured questions (4 easy, 4 medium, 2 hard).

After each answer is saved, the learner sees whether that selected answer was correct or incorrect on the same question and chooses when to continue. The correct option is not revealed. This feedback can affect later answers, so document that the feedback-enabled flow was used when interpreting or comparing research sessions. The current database does not record a Quiz protocol version.

If a request fails, keep the learner code and browser profile, reconnect, and use **Retry / Recover Quiz evidence**. After a refresh, open Quiz Assessment and enter the same code. An unfinished session can be ended only after all existing writes are saved; ending it leaves the exported completion flag false. The gate uses a browser Web Lock to allow one collection tab and requires current Chrome or Edge. Browser storage or profile deletion can destroy unsent evidence.

## Export

Set a private `QUIZ_COLLECTION_EXPORT_KEY` of at least 16 characters in the backend environment. In the Quiz researcher gate, enter that key under **Download Quiz CSV files**. The endpoint returns a ZIP containing `quiz_sessions.csv`, `quiz_responses.csv`, and `manifest.json`; it performs a read-only export. Do not put the key in frontend build variables or share the ZIP outside approved research storage.

From `backend/`, the command line alternative is:

```powershell
python -m scripts.export_quiz_collection --output-dir ..\exports\quiz-collection-local
```

The command reads `DATABASE_URL` from backend settings unless `--database-url` is supplied. Remote database reads require the explicit `--allow-remote-read` flag and separate researcher authorization. Never put a real database URL with credentials on a shared command line. Choose a new output directory on each run. The CSVs include incomplete sessions, source database IDs, recorded timestamps, and question-level evidence; they do not add ML labels.

## Limits before school use

The `STU_` code is caller supplied and is not proof of a roster or consent record. The Quiz question bank and Sinhala wording are still prototype material requiring teacher review. Existing Quiz ORM tables are reused without a new migration; verify the target database schema and question seed in an authorized nonproduction environment. This implementation has isolated SQLite and mocked-browser coverage, not an actual school-device or live PostgreSQL collection trial.
