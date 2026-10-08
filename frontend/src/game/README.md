# Game component (frontend)

**Owner:** RehanOP007 (Game component). Other components: please don't edit
files here. Open an issue or ask the owner instead.

This is the Equation Game, shown by the **Equation Game** tab in `src/App.tsx`.

| Folder | Purpose |
| --- | --- |
| `phaser/` | Phaser setup (`PhaserGame.tsx`, `GameConfig.ts`) and scenes. `PhaserGame` is the entry point used by `App.tsx`. |
| `data/` | Level definitions (`equationLevels.ts`) |
| `analytics/` | In-memory session tracking (`GameSessionTracker.ts`) |
| `api/` | Calls to the backend `/api/v1/game` routes (`gameRequest` helper in `game.ts`) |
| `activities/`, `i18n/`, `GameActivity.tsx`, `GameSummary.tsx`, `useGameEvents.ts`, `types.ts` | Earlier React-only version of the game, kept for reference |

The backend for this component is `backend/app/modules/game/`.
