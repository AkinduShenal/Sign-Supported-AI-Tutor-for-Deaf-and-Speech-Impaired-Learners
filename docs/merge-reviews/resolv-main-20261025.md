# resolv_main merge verification — 2026-10-25

Merge source: `origin/resolv_main` at `3845572697fe6ebfb583d1fb79e06bb1c86156fd`.
Original main: `4ca3f9f13dae22caf2f942faacf24fed9463f25b`.
Local recovery branch: `backup/main-before-resolv-main-20261025`.

The source already contains the original main commit. The integration was
prepared on `merge/resolv-main-20261025` with a two-parent merge, retaining
both histories, before updating main.

## Compatibility fixes included in the merge

- Retain all 16 existing files in `backend/app/modules/game/ml/public/fonts/`
  that the source branch deleted. No existing main files are deleted.
- Preserve the fixed ten-question Quiz as the default. The approved dynamic
  bank remains available through `VITE_QUIZ_BANK_MODE=dynamic`; the isolated
  draft mode remains available through `VITE_QUIZ_DYNAMIC_DEV=true`.
- Restore the existing Quiz → AI Tutor continuation alongside the new
  Quiz → Game continuation. Both require the selected session's ten answers
  and completion to be saved before closing the collection and navigating.
- Update the curriculum migration head assertion for revision `20261021_0008`.
  Add an isolated upgrade/downgrade regression proving existing Quiz question
  and session rows survive, with their fixed-bank metadata left null.
- Make the ML precision test use an explicitly synthetic worker so it verifies
  evidence validation without depending on a separately installed model runtime.
  Real browser-model tests require the existing optional runtime fixture and
  skip when that runtime is absent. Model version/checksum validation is unchanged.
- Remove trailing whitespace from two added font-license files.

Tutor backend code, `AvatarSignPlayer.tsx`, the avatar sign package,
Non-Improvement backend code, frontend package manifests, and Vite startup
configuration remain identical to original main.

## Verification

| Check | Result |
| --- | --- |
| Original main frontend unit tests | 23 passed |
| Original main backend isolated baseline | 428 passed, 3 skipped, 1 existing PostgreSQL-only failure |
| Merged backend isolated regression | 840 passed, 34 skipped, 1 deselected |
| Merged frontend unit tests | 34 passed |
| TypeScript and Vite production build | Passed; bundle-size warning remains |
| Frontend lint | Exit 0; React hook/ref warnings remain |
| Tutor browser regression | Passed: teaching, 153 clips, playback, grading, mobile, reduced motion and fallback |
| Quiz browser regression | Passed: first answers, three practice tries, refresh recovery, completion, Tutor/Game handoffs and learner-cycle continuity |
| Game browser regression | Passed: Drag & Drop, Hangman, mocked persistence/ML, touch and 390/320px layouts |
| Docker Compose configuration | Passed; unset optional DeepSeek variables produce warnings |
| Configured Supabase schema | Read-only inspection confirms all required Quiz columns/table and Alembic revision `20261021_0008` |

Backend command, from `backend/`:

```sh
DATABASE_URL=sqlite+pysqlite:///:memory: ./.venv/bin/python -m pytest -q \
  --ignore=tests/test_database_queries.py -k 'not test_linear_tutor_evaluation'
```

Frontend checks, from `frontend/`: `npm test`, `npm run build`,
`npm run lint`, `npm run test:e2e`, `node tests/quiz.e2e.mjs`, and
`node tests/gameUi.e2e.mjs`. Quiz/Game browser checks used the installed macOS
Chrome via `QUIZ_TEST_CHROME` / `GAME_TEST_CHROME`.

## Verification limits

The unfiltered backend suite already fails collection on original main because
`tests/test_database_queries.py` imports the missing `app.db.queries` module.
`test_linear_tutor_evaluation` requires the separate PostgreSQL implementation
and fails against the isolated SQLite test database on original main as well.
These existing issues were excluded from the final isolated run and remain
unmodified. The 34 skips cover optional PostgreSQL/private artifact/pinned ML
runtime checks. Live model execution and a full Docker image build were not
verified. Browser tests used disposable local databases or mocked APIs.

No shared database migrations, seeds, learner writes, or application deployments
were performed. The shared database check inspected schema metadata only in a
read-only transaction. Other databases must have migration `20261021_0008`
before running this version, including when using the fixed Quiz bank.
