# Game component (frontend)

Sinhala is the primary language by default in Drag & Drop, Hangman and the Game
selection screen. The **ප්‍රධාන භාෂාව / Primary language** control above the canvas
switches between Sinhala and English. Main headings and buttons give the selected
language greater prominence while retaining the other language; hints, feedback,
progress and summary labels follow the selection. Switching updates existing text
objects without restarting scenes, changing questions, resetting answer buffers
or writing new gameplay events. The choice is shared across modes for the current
page and resets to Sinhala on a fresh page load. Researcher collection/export
controls are unchanged. Sinhala wording remains draft and requires teacher review.

Run `node tests/gameLanguage.e2e.mjs` from `frontend/` for the local mocked-API
browser check of default language, live switching, state preservation, full
desktop sessions/summaries and compact layouts in both modes.

**Owner:** RehanOP007 (Game component). Coordinate edits here with the owner.

For researcher-assigned learner codes, durable pending-write recovery, and the
October 14 visit procedure, see [SCHOOL_COLLECTION_RUNBOOK.md](../../../backend/app/modules/game/SCHOOL_COLLECTION_RUNBOOK.md).
The local functional collection check is `node tests/gameCollection.e2e.mjs`,
with `GAME_COLLECTION_API` explicitly pointing at an isolated loopback backend.
Read [P0_SCHOOL_COLLECTION_READINESS.md](../../../backend/app/modules/game/P0_SCHOOL_COLLECTION_READINESS.md)
for verified scope and remaining deployment/phone limitations.

The researcher panel also offers **Download Game CSV files**: a read-only ZIP
of all saved Game CSVs and their manifest. Configure `GAME_COLLECTION_EXPORT_KEY`
on the backend and enter it in the panel. The browser saves the download; pending
writes block the button. See the school runbook for configuration. A local browser
verification is available with `node tests/gameCsvDownload.e2e.mjs` (isolated
SQLite and a synthetic key; no production database).

For researcher-assigned learner codes, durable pending-write recovery, and the
October 14 visit procedure, see [SCHOOL_COLLECTION_RUNBOOK.md](../../../backend/app/modules/game/SCHOOL_COLLECTION_RUNBOOK.md).
The local functional collection check is `node tests/gameCollection.e2e.mjs`,
with `GAME_COLLECTION_API` explicitly pointing at an isolated loopback backend.
Read [P0_SCHOOL_COLLECTION_READINESS.md](../../../backend/app/modules/game/P0_SCHOOL_COLLECTION_READINESS.md)
for verified scope and remaining deployment/phone limitations.

The **Equation Game** tab in `src/App.tsx` opens a three-card Game selection screen. Drag & Drop and Hangman are playable; Mystery Reveal is visibly marked as coming next. Each playable mode uses the same six-task selection rule (two Easy, two Medium, two Hard), shared `session/GameSession.ts`, the local equation variant bank, and Game-owned backend synchronization. Hangman uses the same questions but asks for the final value of `x` through a keypad. The question bank and Game analytics are separate from the seeded curriculum content.

The Game visuals use the Quiz assessment palette and spacing through `phaser/theme/gameTheme.ts` and `phaser/theme/gameUi.ts`. The content surface and Phaser canvas adapt to desktop and phone widths. [VISUAL_MODERNIZATION.md](VISUAL_MODERNIZATION.md) describes this pass, its browser checks, screenshots, and known limitations. The browser check runs locally with all `/api/` requests mocked: from `frontend/`, run `node tests/gameUi.e2e.mjs`. It requires local Chrome and starts its own Vite server on port 5193.

Architecture, backend fields, and earlier milestones are documented in [GAME_MODAL_FILE_STRUCTURE.md](../../../GAME_MODAL_FILE_STRUCTURE.md) at the repository root. The Game backend lives in `backend/app/modules/game/`. Sign Support and Mystery Reveal gameplay remain future work.
