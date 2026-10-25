# Milestone 3.2 — browser authorization audit

The subsequent, explicitly authorized [PP1 shared-researcher verification flow](../../../backend/app/modules/game/research_inference/PP1_BROWSER_VERIFICATION.md) is a supervised prototype alternative. It does not establish the individual learner/researcher accounts missing in this audit. This document preserves the original audit findings.

**BLOCKED before live integration. Phase A is complete; Phase B was not implemented.**

The inspected application has no authenticated browser principal or server-owned authorization mapping from that principal to a completed Game session. The existing ML bearer/manifest gate correctly protects researcher inference, but the current learner-code entry does not establish who is requesting a prediction. Adding a server-side credential proxy without caller authentication and per-session authorization would expose the researcher's approved inference scope to unauthenticated browsers. No such proxy or live request was added.

## Findings and source references

| Area | Evidence | Implication |
| --- | --- | --- |
| Researcher collection gate | `frontend/src/game/CollectionGate.tsx:83` validates a typed code, sets local state and selects learning context; its browser lock prevents concurrent collection tabs | This is collection coordination, not researcher or learner login |
| Learner-code validation | `frontend/src/game/collectionIdentity.ts:2` accepts `STU_` plus 3–6 digits; `activeCode` is module state | Syntax and browser state do not prove identity. ML approval separately requires exactly three digits; do not broaden it |
| Learning-cycle context | `frontend/src/learningContext.ts:35` creates/selects client-stored context with a browser-generated cycle UUID | Context consistency is not authentication or a server-issued session grant |
| Legacy identity helper | `frontend/src/game/identity.ts:3` explicitly describes the absence of a login system and uses a local identifier | A browser identifier is not an authenticated account |
| API authentication | `backend/app/main.py:11` installs CORS and module routers, with no user-login/session verification dependency; the inspected `compose.yaml` has no authenticating gateway | Allowed origins and `allow_credentials=true` do not authenticate a requester. No trusted upstream identity integration was established by this audit |
| Existing Game ownership fields | `backend/app/modules/game/service.py:51` persists the submitted student/context fields and checks consistency when reusing a session ID | Saved record consistency does not link the request to a verified person. Do not grant ownership merely from `request.student_id` |
| Dedicated ML access | `backend/app/modules/game/research_inference/access.py:103` requires its separate bearer, pinned manifest and exact binding; exclusions/quarantines and configuration are checked before DB dependency | Preserve this gate. It is not a browser login and must not be replaced with a session-ID/code check |
| ML context validation | `backend/app/modules/game/research_inference/service.py:70` matches saved student, concept, cycle and phase before strict extraction | Preserves reviewed research scope; does not authenticate the browser holding a session ID |
| Database protection | `backend/app/modules/game/research_inference/router.py:16` uses the authorization dependency before the read-only research database dependency | No reason to weaken or bypass existing validation for UI convenience |
| CSV export key | `backend/app/modules/game/collection_export.py:29` authenticates only the CSV export; the ML gate rejects credential reuse | It supplies neither learner ownership nor a suitable browser prediction credential |
| Frontend card | `frontend/src/game/phaser/PhaserGame.tsx:142` renders the card without a prediction; `MLProficiencyCard.tsx:13` defaults to unavailable | Safe current state; no model result from another learner is embedded |
| Response interface / label | `frontend/src/game/mlPrediction.ts:5` matches the documented prediction/provenance fields; `config/gameMLConfig.ts:3` only controls label presentation | These are reusable after authorization exists; neither is an access-control mechanism |

The one approved genuine-session ASGI verification established extraction/model reproducibility under private test configuration. It did not authenticate a browser user, create learner accounts, approve new sessions, or authorize ongoing use of the selected learner's prediction.

## Saved-session timing also needs an explicit gate

`GameBackendSync.completeSession()` (`frontend/src/game/api/gameBackendSync.ts:47`) returns a boolean from the acknowledged completion queue. `pendingGameWrites.ts:179` marks completion only after the backend confirms the exact session and completed status.

However, `GameSession.finish()` (`frontend/src/game/session/GameSession.ts:101`) awaits that call but does not propagate its boolean. Both scenes can open a summary and emit the ML preview event with an ID from a started session even if saving failed; they already support a save-unverified/local-results fallback. `getResearchSessionId()` confirms that collection started, not that completion was acknowledged. A future ML controller must check confirmed saved completion explicitly, in addition to authentication and server-side evidence validation. Do not use the results-open event or a non-null session ID alone as permission/readiness to predict.

The shared frontend request helper currently has a 15-second timeout (`frontend/src/game/api/game.ts:6`). The isolated worker has previously needed more than 30 seconds during cold verification, and the private verified configuration uses a 60-second bound. A future dedicated ML request lifecycle needs a bounded timeout/cancellation strategy aligned with this behavior; do not alter all existing Game request timeouts or recording logic.

## Smallest safe implementation plan

1. Establish an approved, server-verified browser identity mechanism. For the current supervised research workflow, an authenticated researcher account with explicitly scoped review permissions is the smallest initial audience. Independent learner access additionally requires verified learner accounts and server-owned account-to-session ownership bindings; student-code entry cannot substitute for either.
2. Add a separate, server-owned grant mapping from authenticated subject to explicitly reviewed Game session/context. Historical grants must be reviewed; never derive them automatically from browser codes, local storage, a supplied session ID or existing unauthenticated creation data. Keep this authorization metadata separate from original Game evidence and teacher labels. Include revocation and expiry in the access policy.
3. Only then add an authenticated browser-facing backend gateway. Verify identity and the exact session grant before any inference lookup, then call the existing protected inference boundary with the dedicated researcher credential retained on the server. Continue enforcing its enabled flag, manifest pin, exact context, exclusions/quarantines, saved-complete evidence, legacy adapter, checksum/runtime and no-store/non-disclosing responses. Do not create an anonymous token-injecting proxy or reuse the CSV key.
4. Connect the presentation component only after completion is positively acknowledged. Bind the request to that current session, cancel on session/learner changes, reject stale/malformed responses, preserve actual probabilities/provenance and keep unavailable/error states without mock fallbacks. Keep the label flag presentation-only. No automatic inference enablement or approval expansion is part of UI wiring.
5. Validate login/grant enforcement and the complete browser-to-gateway-to-model path in an approved private environment before activation. Test denied/revoked/expired access, cross-session ownership, incomplete/excluded/quarantined evidence, disabled service, response/network failures, all card states, both games and learner switching. No browser-held ML secret or lookup-by-ID authorization is permitted.

This plan applies deny-by-default and per-request, per-resource authorization as described by the [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html). An identity provider/transport and grant policy must be selected before implementing it.

**Browser credential constraint:** an ordinary server-managed login can use an opaque `HttpOnly; Secure; SameSite` session cookie, which JavaScript cannot read but the browser sends automatically. It is still an authentication credential in a request header. If the requirement forbids even such cookies, an explicitly approved alternative identity channel is required; this audit does not assume an exception. The ML researcher bearer must stay server-side in either design. See [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

## Tests performed in this audit

Existing isolated backend denial/evidence tests were run against SQLite in memory, without starting the application server or accessing genuine Game records:

```text
python -B -m pytest tests/test_game_research_inference.py -q -p no:cacheprovider
  --basetemp <unique ignored local audit directory>
  -k 'disabled_before_lookup or authentication_before_lookup
      or export_token_cannot_be_reused or invalid_approval_configuration_before_lookup
      or denied_sessions_before_lookup or manifest_context_mismatch
      or invalid_saved_evidence_never_invokes_worker'
```

Result: **50 passed, 11 deselected**, one existing Starlette TestClient deprecation warning. Both synthetic game-mode fixtures were exercised. Coverage includes disabled inference, missing/invalid researcher bearer, forbidden CSV-key reuse, missing/bad approval manifest, unapproved/excluded/quarantined sessions, all manifest-context mismatch fields, incomplete sessions, missing evidence, invalid chronology, inconsistent aggregates and malformed payloads. These checks reject requests before the model worker is invoked.

Successful live browser prediction, user-authenticated ownership, frontend network failures and complete browser-to-model integration were **not tested** because their prerequisite identity/grant architecture is absent. The prior Milestone 3.1 layout/formatting/label tests were not rerun or relabelled as live-integration tests. No frozen model load, live ML prediction or external database query was performed in this audit. Only synthetic in-memory fixture setup records were created by pytest.

The normal application and private research configuration both report `GAME_ML_EXPERIMENTAL_ENABLED=false`. No secrets were printed, no active approvals were added and the selected historical learner was not reused.

## Changes and status

Created only this audit document. No application, frontend behavior, endpoint, authorization, environment file, deployment setting, dependency, model, original research result, teacher assessment or Game source record was changed. Pytest temporary artifacts are under the ignored local artifacts directory.

**Milestone status: BLOCKED at the Phase A identity/authorization gate.** The remaining work is an approved identity and per-session grant architecture, followed by secure integration and its live tests. The ML card remains unavailable and the model remains disabled for normal browser flows.
