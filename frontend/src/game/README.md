# Game component (frontend)

**Owner:** RehanOP007 (Game component). Other components: please don't edit
files here. Open an issue or ask the owner instead.

This is the Equation Game, shown by the **Equation Game** tab in `src/App.tsx`.

Current working-tree state (2026-10-11): a selection hub offers Drag & Drop
(playable), Hangman and Mystery Reveal (unavailable). Drag & Drop uses the shared
`session/GameSession.ts`, six selected tasks from 18 local variants, persisted
analytics and draft bilingual labels. The curriculum seed does not replace this
local bank. Latest frontend checks: 26 tests passed; build passed with a bundle
warning; lint passed with five existing Tutor/avatar React warnings. Browser
acceptance of the latest hub remains to be verified.

**Full file-by-file structure, architecture, database shape, Milestone 3
progress and known gaps:** see
[`GAME_MODAL_FILE_STRUCTURE.md`](../../../GAME_MODAL_FILE_STRUCTURE.md)
at the repo root — that document is the source of truth for this
component, kept up to date as the single continuation guide. This file is
intentionally just a pointer.

The backend for this component is `backend/app/modules/game/`.
