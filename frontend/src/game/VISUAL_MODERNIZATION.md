# Game visual modernization — 12 October 2026

This pass updates the Game selection, Drag & Drop, and Hangman presentation to match the Quiz assessment UI. It leaves question data, scoring, analytics, GameSession, backend requests, and figure mechanics in their existing modules. All browser checks use mocked Game API responses; no database is needed.

## 1. Files created

- `phaser/theme/gameTheme.ts`: numeric Phaser colors and reusable design tokens.
- `phaser/theme/gameUi.ts`: rounded panels, buttons, progress steps, text resolution, and phone viewport/touch helpers.
- `tests/gameUi.e2e.mjs`: isolated local Chrome interaction test and canvas screenshot capture.
- This report.

## 2. Files modified

- `src/App.css` only for `.game-page` and `.phaser-game-container` presentation.
- `phaser/GameConfig.ts`, `phaser/PhaserGame.tsx`, and `phaser/viewport.ts` for backing resolution and responsive sizing.
- `phaser/scenes/GameSelectionScene.ts`, `phaser/scenes/EquationGameScene.ts`, and `phaser/scenes/HangmanGameScene.ts` for visual layout and control styling.
- `phaser/BalanceScale.ts` for themed colors and rounded pans.
- `src/game/README.md` for the current Game overview.

The user's existing `src/App.tsx` edit was present before this pass and was not changed here. The Game question bank, GameSession, tracker, API, Hangman figure, backend, Quiz, Tutor, and curriculum files were not edited in this pass.

## 3. Shared theme

`gameTheme.ts` follows the Quiz's light page, white surfaces, purple primary, soft borders, dark text, and 20–24 px card corners. `gameUi.ts` uses these tokens for all three scenes. Buttons have primary, secondary, quiet, and unavailable visual states; their existing callbacks remain in their scenes. English labels and their existing Sinhala labels have separate lines and more room. Progress is a six-node stepper with numbers and stars, so its meaning does not depend on color.

## 4. Sharpness and scaling

The installed Phaser 4 `Scale.RESIZE` path sized the canvas backing buffer to the parent CSS width. On a high-density screen, one rendered game pixel was enlarged to multiple device pixels. Phaser Text also starts with texture resolution 1, and camera zoom enlarged that texture again. The former fixed 800 × 640 / 420 × 770 layouts could further enlarge text on desktop or shrink controls on phones. The canvas was not enlarged by a separate CSS transform.

The host now sizes the backing buffer to the CSS surface times `devicePixelRatio`, capped at 2 to bound memory and fill cost. `Scale.NONE` and an inverse scale zoom keep the visible canvas at the CSS size. Game text textures use camera-aware resolution capped at 3. The camera limits desktop enlargement and rounds pixels. In a local DPR 2 desktop check, the canvas measured 2196 backing pixels across for 1098 CSS pixels; text resolution was about 2.46. Phaser is still rasterized, so tiny text and noninteger zoom cannot look exactly like DOM text.

## 5. Selection

The three modes appear as rounded cards with vector icons, bilingual names/descriptions, and consistent actions. Drag & Drop and Hangman can launch from the whole card. Mystery Reveal has a readable locked icon and the existing “Coming next” wording; it does not launch gameplay.

## 6. Drag & Drop

The equation, balance scale, drop zone, operation tiles, hint, feedback, reward, and Next control have clearer spacing and matching colors. The compact layout stacks operation tiles in two rows. The same draggable containers, drop zone, answer handlers, and analytics calls remain. A quiet Menu button returns to selection during a task.

## 7. Hangman

Desktop puts math/keypad and the illustrated figure in separate light panels. Phone stacks the figure above the equation and keypad. The keypad, Submit Answer, Hint, Next, and Menu use the shared button style. `HangmanFigure.ts` and the existing ten-slip fall, expressions, celebration, and confetti behavior were not changed.

## 8. Responsive input and accessibility

The phone design is 420 × 1120 game units and scrolls inside the regular page instead of shrinking the whole scene to one screen. Desktop uses a 960 × 840 design. Interactive control heights are raised to at least 44 CSS pixels. Empty canvas space permits native page scrolling, while touches beginning on an interactive Game control keep Phaser touch capture for taps and dragging. Phaser 4 may emit a resize when only the canvas's viewport position changes during a page scroll; the UI rebuilds scenes only when canvas dimensions actually change. That prevents a scroll from restarting the current question. Actual orientation/size changes still use the existing scene restart path and preserve selected variants and progress.

Text and symbols accompany success, error, and progress colors. No audio is needed. This pass adds no animation; existing reduced-motion paths are preserved.

## 9. Regression checks

Run from `frontend/`:

```powershell
npm.cmd run build
npm.cmd run lint
npm.cmd test
node tests/gameUi.e2e.mjs
```

The browser script starts isolated local Vite and Chrome processes, intercepts Game API calls, checks actual mouse/touch targets and six-task completion, and saves PNGs and `verification.json` in ignored `frontend/artifacts/game-ui/`. It checks 390 px and 320 px phones, 44 px targets, native page scrolling, touch dragging, landscape resize, Hangman's ten-error fall, and reduced-motion fall. Backend responses are mocked, including an unavailable-results fallback; this does not prove production backend integration or physical-device behavior.

The frontend build and 39 unit tests pass. Lint exits successfully with five warnings in unchanged Tutor/Avatar React files. Vite reports its existing large-chunk advisory. The isolated browser regression should be rerun after future changes to this UI.

## 10. Known limitations

- The original Phaser 4 Drag & Drop handlers can count a missed drag as a tap: dragstart sets a flag, then the card's pointerdown handler resets it. This affects input semantics, so it was left for a separate behavior change.
- The existing Hangman confetti code may still animate when reduced motion is requested; the existing instant fall path is preserved. Changing confetti would affect `HangmanFigure.ts`, which this visual pass does not modify.
- Browser checks use Chrome emulation and mocked backend calls. Test on a physical phone and with the Game backend before release.
- Some existing Sinhala copy is draft and needs the team's usual language review. No translations were rewritten here.

## 11. Game feel pass — 16 October 2026

Visual-only. Question data, scoring, analytics, GameSession and backend calls are unchanged.

- `phaser/theme/gameBackdrop.ts`: a soft game-world backdrop (sky gradient, hills, drifting clouds, faint maths symbols) behind every Game scene, drawn well past the design edges so letterboxing never shows blank strips.
- `phaser/theme/gameEffects.ts`: shared feedback — confetti, ✓/✕ badge pops, a star that flies into the progress path, shakes, and a level banner. No sound; nothing blocks input; every effect has a reduced-motion path.
- `phaser/HangmanFigure.ts`: rewritten as a procedurally animated gymnast on a gym bar above a crash mat. Idle sway and blinking; each wrong answer visibly slips one finger off the bar in a realistic order — on each hand the thumb first, then little, ring, middle and finally index, hands alternating right first (the finger flicks open, the hand jolts, the body swings, a sweat drop from the third slip); once one hand has no fingers left it lets go and the figure hangs from the other. A correct answer never changes the grip — the figure does two pull-ups with kicking legs and confetti. The fall drops onto the mat, which squashes like a cushion: no impact effects, no injury (Milestone 4 §7/§9/§18).
- `HangmanGameScene.ts`: re-laid out so both panels share edges, Submit and Hint share one row (Hint previously ran past the panel bottom), a ten-pip grip meter with an always-visible "Attempts Left", and a 4-column keypad on phones.
- `viewport.ts`: the wide design width now follows the canvas aspect ratio (960–1360) and scenes keep it for their lifetime; a resize only refits the camera and re-rasterises text (`resharpenSceneText`).
- `phaser/PhaserGame.tsx` + `PhaserGame.css`: a full-screen button on the game stage (browser Fullscreen API with a CSS overlay fallback for iPhone); the language toggle stays available in full screen. `App.css` was not changed.
- Confetti and banners never originate on, or sit over, an equation.

`tests/gameUi.e2e.mjs` now opens the Game tab first (the app's default tab changed). Its phone→landscape step still expects Hangman to switch to the wide layout on rotation, which Hangman has not done since its resize handler stopped restarting the scene; that assertion fails independently of this pass.

## 12. Game typography — 16 October 2026

- Bundled fonts in `assets/fonts/` (SIL OFL 1.1, licences beside the files): Fredoka for Latin letters and digits, Noto Sans Sinhala (real variable weights) for Sinhala. Declared in `phaser/PhaserGame.css`, served from the app bundle (no third-party font requests), and awaited by `phaser/gameFonts.ts` before the canvas boots, because Phaser rasterises Text once. If they fail to load within 3 s, the system fallback fonts in `FONT_FAMILY` are used.
- `bilingualPair(..., { variant: 'title' })`: chunky outlined screen titles (deep purple fill, thick white outline, solid drop shadow) for Choose Your Game, Balance the Equation and Hangman; `variant: 'heading'` for bold card names. Button labels are bold in both languages (real bold, never synthetic).
- `hudChip()`: rounded HUD pills behind the level line and the Drag & Drop instruction, resized automatically when the language toggle changes the text.
- Equations and pans use semi-bold (600), not bold: at full bold the variable x starts to resemble the × operator.
