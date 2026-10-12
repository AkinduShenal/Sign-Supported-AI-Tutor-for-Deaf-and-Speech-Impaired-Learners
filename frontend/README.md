# Frontend — accessible mathematics research prototype

Current working-tree status: **2026-10-11**. React, TypeScript and Vite provide
state-based navigation in `src/App.tsx`; the default tab is currently Game.

| Gateway | Entry point | State |
| --- | --- | --- |
| Quiz Assessment | `src/quiz/QuizAssessment.tsx` | Bilingual ten-question pre-assessment, saved responses/confidence and provisional diagnostic results. |
| Equation Game | `src/game/phaser/PhaserGame.tsx` | Mode-selection hub; Drag & Drop playable, Hangman/Mystery Reveal unavailable. |
| AI Tutor | `src/components/AdaptiveTutor.tsx` | Adaptive lesson workspace, examples, practice and prototype avatar support. |
| Remedial Support | Placeholder in `src/App.tsx` | Integration pending. |

These gateways are not an automatic shared Quiz → Game → Tutor learning cycle.
Quiz and Game share a pseudonymous browser identity helper but do not propagate
one coordinated learning-cycle ID. Tutor currently imports diagnostic JSON.
The new shared curriculum seed does not automatically feed any of these screens.

## Development and checks

From this directory, with dependencies already installed:

```sh
npm run dev
npm run test
npm run build
npm run lint
```

Use `npm.cmd` on Windows if PowerShell blocks `npm.ps1`. API calls use
`VITE_API_BASE_URL`, normally `http://127.0.0.1:8000/api/v1`. Compose can
configure different frontend/backend ports; inspect its environment settings.

Verified for this documentation refresh: **26 tests passed**; TypeScript/Vite
build passed with a large-bundle warning; Oxlint completed with **5 existing
React effect/ref warnings** in Tutor/avatar components. These checks do not
replace a browser accessibility or learner walkthrough. No browser E2E suite
was run for this refresh.

Game/Tutor labels and Quiz content require Sinhala/teacher review. The avatar
actions are prototype gestures, not human-validated Sri Lankan Sign Language.
Validated-only playback is the default; unvalidated review requires explicit
opt-in. Existing heuristics are not trained ML or evidence of learning gains.

See [project status](../STATUS_CHECKLIST.md),
[Game guide](../GAME_MODAL_FILE_STRUCTURE.md),
[Tutor guide](../docs/GRADE10_TUTOR.md) and
[database status](../DATABASE_CHECKLIST.md). Preserve component ownership and
unrelated local changes when working on shared `App.tsx`.
