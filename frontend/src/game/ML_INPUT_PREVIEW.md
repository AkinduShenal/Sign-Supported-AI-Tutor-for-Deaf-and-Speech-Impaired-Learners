# Game ML input research preview

After completing Drag & Drop or Hangman, expand **ML Input Details — Research Preview** below the existing canvas result. **Copy ML Features** copies one JSON object with exactly nine numeric/null fields. The visible JSON can also be selected manually if clipboard permission is unavailable. Refresh evidence retries only the read request.

The panel reads `GET /api/v1/game/results/{game_session_id}/ml-inputs`. This endpoint performs SELECTs only. It never saves/recalculates a result, changes an event, loads a model or updates a learner. The existing result endpoint, heuristic indicators, scoring, question selection and recording protocol are unchanged.

| Feature | Evidence and definition |
| --- | --- |
| first_attempt_accuracy | Correct numbered first outcomes / all planned steps, matching `ResearchObservation.first_attempt_accuracy`. Saved QUESTION_SHOWN and completion coverage, task summaries and outcome chronology must reconcile. Drag & Drop counts operation steps. Hangman counts one final-answer step per task. Missing/ambiguous evidence returns null. |
| game_success_rate | Saved `GameResult.game_success_rate`: successful tasks / attempted tasks, including eventual success after retries. |
| wrong_attempt_count | Saved result total of task wrong attempts. |
| retry_count | Saved result count of RETRY_STARTED events. |
| total_hint_count | Saved result sum of task hints. |
| skipped_step_count | Actual saved result skipped-step total; no substitution or fabrication. Current scenes have no skip control, so stored zero is not proof of independently observed skipping behavior. |
| game_active_time_sec | Saved rounded sum of task durations. Recorded elapsed task seconds, not verified active engagement or reliability-approved research duration. |
| game_hint_rate | Saved share of the six tasks with at least one hint, not hints per task or hinted steps per planned step. |
| game_avg_attempts_per_task | Saved total submissions / attempted tasks; multi-operation tasks can require multiple submissions even with no mistakes. |

Values are copied without display rounding or conversion to percentage strings. Missing, invalid or context-inconsistent evidence becomes null and the panel marks the record not ready for inference. Eight stored metrics can remain available even when the evidence needed for first-attempt accuracy is missing. No local-tracker fallback is substituted for saved evidence.

## Colab demonstration boundary

1. Play a session, reach Results and wait until the collection is saved.
2. Expand the research preview. Check the nine values and availability messages.
3. Click **Copy ML Features** and paste into a JSON input cell in Colab.
4. Verify the actual trained model's feature names, order, definitions, units and preprocessing before prediction. Do not replace null with zero to force inference.
5. Only a model trained with this exact nine-feature contract can consume this object directly. Run prediction in that notebook, not in the Game.

The repository's existing research artifacts use `gameplay_score` with up to twelve behavior features. In particular, their `hint_usage_rate` is step-based and their duration features are masked when unreliable. Renaming this panel's nine keys cannot make those artifacts compatible. The separately trained nine-feature Colab definitions have not yet been supplied, so `ready_for_inference` remains false even if all nine recorded values are available. No trained Game prediction is integrated by this preview.

## Focused local verification

From `backend/`, run `python -B -m pytest -p no:cacheprovider tests/test_game_ml_preview.py` in the configured backend environment. It uses synthetic in-memory SQLite evidence and checks that the preview executes only SELECTs.

From `frontend/`, run `node --experimental-strip-types --test tests/mlInputFeatures.test.ts`. For browser verification in PowerShell, set `$env:GAME_ML_PREVIEW_ONLY='1'`, then run `node tests/gameUi.e2e.mjs`. The browser test launches isolated loopback Vite/Chrome with synthetic mocked APIs, checks both completed modes, clipboard success/null handling and 390/320px panel layouts, and saves screenshots under `frontend/artifacts/`. It does not connect to a database or train a model.
