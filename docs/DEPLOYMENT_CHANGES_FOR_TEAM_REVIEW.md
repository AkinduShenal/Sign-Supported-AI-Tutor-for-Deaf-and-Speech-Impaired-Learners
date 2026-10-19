# Deployment preparation archive and team review ? October 16, 2026

**Status: deployment preparation withdrawn locally pending team discussion.**
**Rollback source verification: PASSED. Post-rollback checks: PASSED with the Windows test-path retry described below.**

The owner requested that the deployment changes be documented and reverted before
team review. This file preserves the change rationale, effects, verification record,
and complete archived patch. Its code blocks are historical material, not active
configuration or approval to restore/deploy anything.

The backend is already hosted on Railway. The intended architecture was Vercel
frontend ? existing Railway FastAPI service ? existing authorized Supabase PostgreSQL.
Public backend API base supplied by the owner:
`https://backend-production-b489d.up.railway.app/api/v1`.
The Vercel production domain was not selected. No hosting account settings, Railway
environment variables, Supabase data/schema, commits, pushes, merges or branches were
changed by the deployment preparation or this rollback.

## What was prepared and why it is being reverted

| File | Preparation change | Effect if committed/deployed | Rollback action |
| --- | --- | --- | --- |
| `backend/app/main.py` | App factory; hosted Game dependency; revised hosted CORS; synthetic-target health marker | Railway Game routes would return 503. Hosted localhost CORS was removed for all modules, so team browser clients could be affected | Restore pre-preparation tracked version |
| `backend/app/core/config.py` | Optional validated `CORS_ORIGINS` | Adds allowed frontend origins; malformed values could prevent startup | Restore pre-preparation tracked version |
| `frontend/src/main.tsx` | Optional `VITE_GAME_COLLECTION_ONLY` entry | `true` selects a Game-only shell; false/unset selects normal team app | Restore direct normal-app import |
| `.env.example` | Public Railway URL and deployment setting descriptions | Example only; copying production settings into local development could target the live API | Remove deployment additions |
| `frontend/vite.config.ts` | Production URL validation and common public-secret-name rejection | Production build would fail without an HTTPS API URL; local builds using localhost were rejected | Restore original Vite config |
| `frontend/src/game/CollectionGate.tsx` | Production unavailable screen | Prevents Game mount, learner controls, storage recovery and requests in production builds, including local preview | Restore original collection gate |
| `frontend/src/game/api/collectionStore.ts` | Reuse the Game transport's API base | Keeps pending evidence destination aligned with HTTP transport | Restore original destination expression |
| `frontend/tests/gameCollection.e2e.mjs` | Synthetic target handshake, explicit Game entry flag, longer initial form wait | Rejects local APIs backed by remote databases; depends on the added health marker | Restore original simulator file |
| `frontend/tests/gameCsvDownload.e2e.mjs` | Explicit Game entry flag | Makes the browser test independent of the normal app's default tab | Restore original browser test file |

The shared files created integration and merge-overlap concerns. The user chose to
withdraw the preparation and discuss it with the team before deciding how to proceed.
Restoring these files removes this task's deployment-related diff, but cannot guarantee
that unrelated Game/ML changes will merge without conflicts with other branches.

## Added files consolidated into this archive and removed from active source

- `backend/app/core/game_deployment.py`: Railway detection, exact HTTPS origins, closed Game authorization dependency.
- `backend/app/core/collection_safety.py`: local synthetic database target validation.
- `backend/tests/test_game_deployment.py`: hosted Game denial, preserved shared routes, CORS and synthetic-target checks.
- `frontend/src/game/GameCollectionApp.tsx`: dedicated Game shell.
- `frontend/src/game/CollectionUnavailable.tsx`: production collection unavailable message.
- `frontend/tests/gameCollectionRecovery.test.ts`: pending recovery, switching and independent device queue checks.
- `frontend/tests/gameProductionGate.e2e.mjs`: production browser block verification with API requests intercepted/aborted.
- `frontend/vercel.json`: Vite install/build/output settings, SPA fallback and response headers.
- `frontend/.env.example`: public production settings; the owner's latest `VITE_GAME_COLLECTION_ONLY=false` value is preserved in the archived patch.
- `docs/GAME_DEPLOYMENT.md`: Vercel/Railway steps, environment, smoke checks, data risks and rollback guidance.
- `docs/GAME_ACCESS_CONTROL_PROPOSAL.md`: staff-controlled access recommendation, not implemented or approved.
- `docs/GAME_DEPLOYMENT_VERIFICATION.md`: historical local test results and limitations.
- `docs/GAME_TEACHER_GUIDE.md`: conditional future collection instructions, not an available verified website.

The earlier `render.yaml` and `backend/app/collection_main.py` had already been
removed when the owner corrected the host to Railway. They are not part of the final
Railway patch and must not be recreated as a replacement backend deployment.
The ignored `tmp/deployment_synthetic_api.py` helper is also archived separately below
and removed. Synthetic database/export/browser evidence is retained in ignored local
folders; it is not school data and must not be merged as learner observations.

## Team decisions needed before resuming

1. Decide which shared files the Game owner may change and separate frontend-only
   hosting preparation from any approved shared Railway release.
2. Review existing Railway frontend origins, deployment branch and auto-deploy behavior
   before any push. Preserve Quiz/Tutor clients and the existing Supabase connection.
3. Select the Vercel domain and review exact CORS origins; do not use wildcard previews.
4. Approve staff authentication and learner/session authorization before student access.
   `STU_001`-style codes and Game UUIDs are identifiers, not credentials.
5. Approve production/database access and verify the complete Vercel ? Railway ?
   Supabase saving workflow before teacher handoff. No automatic migrations or resets.

Only narrow static researcher export-key dependencies were found in Game/Quiz; no
reusable staff sign-in/session ownership system was found in the repository. The
proposal was invited staff-only managed Supabase Auth, backend-managed sessions and
per-device grants locked to the selected learner code/Game sessions before handoff.
Students would need no accounts; broader researcher exports would use separately
authenticated researcher access. Provider approval, session storage, recovery,
revocation, cross-site cookie/CSRF handling and cross-module Game access remain
unresolved. Nothing in that proposal was implemented or enabled.

**After rollback, the added production safeguards are absent.** Restoring the original
code does not make internet student collection safe or authorized. Do not deploy the
restored anonymous Game routes or use the live Railway API for synthetic gameplay
while this work is under team review.

## Historical checks before rollback

- Both frontend production entry variants built successfully with the public Railway URL.
- Frontend unit tests: 16 passed (including two deployment-added Game queue tests).
- Game/deployment/export/ML/research backend set: 278 passed, 2 optional PostgreSQL checks skipped.
- Tutor backend checks: 76 passed in a separate SQLite-only process.
- Quiz checks: 21 passed, 1 failed at `test_quiz_seed.py:117` because `is_correct` was present.
  The same failure reproduced with the original committed FastAPI entry loaded in memory.
- Production frontend browser check: no learner controls/canvas, no API requests,
  and no pending-storage recovery/clearing. The test aborted API requests before networking.
- Earlier local-development recording browser run passed Drag & Drop and Hangman into
  disposable SQLite, including response-loss retries, refresh/tab-close recovery and switching.
- Read-only SQLite/CSV reconciliation matched 6 sessions, 4 completed results,
  2 incomplete sessions and 37 browser answers with unique retry event keys.
- Game language browser regression failed the summary text bounds assertion at
  `gameLanguage.e2e.mjs:248`; visual source was left untouched by deployment preparation.
- Python lint and diff/asset checks passed. Live Railway liveness could not be verified
  from the execution environment; no outage was established.
- Hosted saving, actual PostgreSQL concurrency/schema/TLS and access controls were NOT VERIFIED.

These are historical results, not claims that the reverted source includes the removed
safeguards/tests. Separate post-rollback checks are recorded below when completed.

## Rollback scope and evidence

Base commit for the archived tracked patch: `65e51d9ab2b508515bf9f4f5afaf7b1857c20a26`.
Branch retained: `feature_game-modal_v1`.
Preserved unrelated changed/untracked files: **23**; their byte hashes
were captured before rollback and will be checked afterward.

Files preserved without modification:

- `CLAUDE.md`
- `backend/app/modules/game/ml/ML_Milestone_2_2.md`
- `backend/app/modules/game/ml/RESEARCH_README.md`
- `backend/app/modules/game/ml/SESSION_VERIFICATION.md`
- `backend/app/modules/game/ml/collection_research.py`
- `backend/app/modules/game/ml/research_dataset.schema.json`
- `backend/app/modules/game/ml/research_schema.py`
- `backend/app/modules/game/ml/session_verification.py`
- `backend/tests/test_game_collection_research.py`
- `backend/tests/test_game_session_verification.py`
- `frontend/src/game/VISUAL_MODERNIZATION.md`
- `frontend/src/game/phaser/HangmanFigure.ts`
- `frontend/src/game/phaser/PhaserGame.css`
- `frontend/src/game/phaser/PhaserGame.tsx`
- `frontend/src/game/phaser/scenes/EquationGameScene.ts`
- `frontend/src/game/phaser/scenes/GameSelectionScene.ts`
- `frontend/src/game/phaser/scenes/HangmanGameScene.ts`
- `frontend/src/game/phaser/theme/gameBackdrop.ts`
- `frontend/src/game/phaser/theme/gameEffects.ts`
- `frontend/src/game/phaser/theme/gameTheme.ts`
- `frontend/src/game/phaser/theme/gameUi.ts`
- `frontend/src/game/phaser/viewport.ts`
- `frontend/tests/gameUi.e2e.mjs`

## Reconsidering the archive later

Do not apply this patch automatically after merging teammate work. Its tracked hunks
are based on the commit above and may overlap new team changes. Review each behavior,
port only approved parts, include their dependencies, and rerun relevant checks.
The archived guides contain historical status and commands referring to files removed
by rollback; they must not be followed as current deployment instructions.
No production credentials, real environment files or exported learner data are included.

## Complete withdrawn deployment patch

The following patch contains the final tracked changes and all thirteen added files
as they stood immediately before rollback. It is retained for discussion and selective
future reimplementation, not automatic deployment.

````diff
diff --git a/.env.example b/.env.example
index 4a6d690..4e551c5 100644
--- a/.env.example
+++ b/.env.example
@@ -1,6 +1,21 @@
 FRONTEND_PORT=5173
 BACKEND_PORT=8000
 
+# Frontend PUBLIC build settings (set in Vercel; never put secrets in VITE_*).
+# Production builds require an explicit HTTPS backend URL ending in /api/v1.
+VITE_API_BASE_URL=https://backend-production-b489d.up.railway.app/api/v1
+VITE_GAME_COLLECTION_ONLY=false
+
+# Existing Railway backend uses app.main:app; retain the shared service.
+# Railway system IDs automatically keep Game blocked in the prepared code.
+# Inspect FRONTEND_URL before proposing approved Railway environment changes.
+# FRONTEND_URL=https://your-approved-frontend.example
+# Optional additional exact origins (additive to FRONTEND_URL):
+# CORS_ORIGINS=["https://your-approved-frontend.example"]
+# DATABASE_URL must use postgresql+psycopg:// and SSL for production.
+# GAME_COLLECTION_EXPORT_KEY is the existing backend-only researcher export
+# credential; it does not enable production collection or learner access.
+
 DATABASE_URL=replace_with_shared_supabase_database_url
 
 # Local lesson retrieval works without an API key.
diff --git a/backend/app/core/config.py b/backend/app/core/config.py
index 3645d9e..ba1ad7e 100644
--- a/backend/app/core/config.py
+++ b/backend/app/core/config.py
@@ -2,7 +2,9 @@ from functools import lru_cache
 from pathlib import Path
 
 from pydantic_settings import BaseSettings, SettingsConfigDict
-from pydantic import Field, SecretStr
+from pydantic import Field, SecretStr, field_validator
+
+from app.core.game_deployment import validate_https_origin
 
 # Repo-root .env (backend/app/core/config.py -> backend/app/core -> backend/app
 # -> backend -> repo root). Docker Compose already injects DATABASE_URL as a
@@ -21,6 +23,8 @@ class Settings(BaseSettings):
     )
 
     frontend_url: str = "http://localhost:5173"
+    # Additive origins; FRONTEND_URL remains supported by the shared service.
+    cors_origins: list[str] = Field(default_factory=list)
     rag_enabled: bool = True
     rag_generation_enabled: bool = False
     rag_top_k: int = Field(default=3, ge=1, le=5)
@@ -28,6 +32,11 @@ class Settings(BaseSettings):
     rag_model: str = "gpt-4.1-mini"
     openai_api_key: SecretStr | None = None
 
+    @field_validator("cors_origins")
+    @classmethod
+    def validate_cors_origins(cls, values: list[str]) -> list[str]:
+        return [validate_https_origin(value) for value in values]
+
     model_config = SettingsConfigDict(
         env_file=ENV_FILE,
         extra="ignore",
diff --git a/backend/app/main.py b/backend/app/main.py
index e0b740d..f0f153f 100644
--- a/backend/app/main.py
+++ b/backend/app/main.py
@@ -1,47 +1,59 @@
-from fastapi import FastAPI
+import os
+
+from fastapi import Depends, FastAPI
 from fastapi.middleware.cors import CORSMiddleware
 from sqlalchemy import text
 
-from app.core.config import settings
+from app.core.collection_safety import synthetic_collection_allowed
+from app.core.config import Settings, settings
+from app.core.game_deployment import (
+    configured_cors_origins,
+    is_hosted_runtime,
+    require_approved_collection_access,
+)
 from app.db.session import engine
 from app.modules.game.router import router as game_router
 from app.modules.quiz.router import router as quiz_router
 from app.modules.tutor.router import router as tutor_router
 
 
-app = FastAPI(
-    title=settings.app_name,
-    version="0.1.0",
-)
-
-app.add_middleware(
-    CORSMiddleware,
-    allow_origins=[settings.frontend_url],
-    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
-    allow_credentials=True,
-    allow_methods=["*"],
-    allow_headers=["*"],
-)
-
-app.include_router(tutor_router)
-app.include_router(game_router)
-app.include_router(quiz_router)
-
-
-@app.get("/api/v1/health", tags=["System"])
-def health_check() -> dict[str, str]:
-    return {
-        "status": "ok",
-        "service": "sign-supported-ai-tutor-api",
-    }
-
-
-@app.get("/api/v1/db-health", tags=["System"])
-def database_health_check() -> dict[str, str]:
-    with engine.connect() as connection:
-        connection.execute(text("SELECT 1"))
-
-    return {
-        "status": "ok",
-        "database": "connected",
-    }
+def create_app(config: Settings = settings) -> FastAPI:
+    hosted = is_hosted_runtime()
+    app = FastAPI(title=config.app_name, version="0.1.0")
+    app.add_middleware(
+        CORSMiddleware,
+        allow_origins=configured_cors_origins(config.frontend_url, config.cors_origins, hosted),
+        allow_origin_regex=None if hosted else r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
+        allow_credentials=True,
+        allow_methods=["*"],
+        allow_headers=["*"],
+    )
+
+    # Preserve the shared Railway application and its existing business modules.
+    app.include_router(tutor_router)
+    app.include_router(
+        game_router,
+        dependencies=[Depends(require_approved_collection_access)] if hosted else [],
+    )
+    app.include_router(quiz_router)
+
+    @app.get("/api/v1/health", tags=["System"])
+    def health_check() -> dict[str, str | bool]:
+        return {
+            "status": "ok",
+            "service": "sign-supported-ai-tutor-api",
+            "synthetic_collection_allowed": not hosted and synthetic_collection_allowed(
+                config.database_url, os.getenv("GAME_SYNTHETIC_COLLECTION") == "true",
+            ),
+        }
+
+    @app.get("/api/v1/db-health", tags=["System"])
+    def database_health_check() -> dict[str, str]:
+        with engine.connect() as connection:
+            connection.execute(text("SELECT 1"))
+        return {"status": "ok", "database": "connected"}
+
+    return app
+
+
+app = create_app()
diff --git a/frontend/src/game/CollectionGate.tsx b/frontend/src/game/CollectionGate.tsx
index 404ed46..e2ddf77 100644
--- a/frontend/src/game/CollectionGate.tsx
+++ b/frontend/src/game/CollectionGate.tsx
@@ -4,9 +4,17 @@ import { setCollectionStudent, validateStudentCode } from './collectionIdentity'
 import { getCollectionStore, openCollectionStore } from './api/collectionStore'
 import { CollectionExport } from './CollectionExport'
 import { GameLanguageToggle } from './GameLanguageToggle'
+import { CollectionUnavailable } from './CollectionUnavailable'
 import './CollectionGate.css'
 
 export function CollectionGate({ children }: { children: ReactNode }) {
+  // The hosted API may not have the new safeguard yet. Never mount collection,
+  // recover browser evidence or send Game writes in a production build.
+  if (import.meta.env.PROD) return <CollectionUnavailable />
+  return <DevelopmentCollectionGate>{children}</DevelopmentCollectionGate>
+}
+
+function DevelopmentCollectionGate({ children }: { children: ReactNode }) {
   const [lock, setLock] = useState(false)
   const [code, setCode] = useState('')
   const [active, setActive] = useState<string | null>(null)
diff --git a/frontend/src/game/api/collectionStore.ts b/frontend/src/game/api/collectionStore.ts
index f03ac62..795d718 100644
--- a/frontend/src/game/api/collectionStore.ts
+++ b/frontend/src/game/api/collectionStore.ts
@@ -1,12 +1,13 @@
 import { completeGameSession, createGameSession, saveTaskAttempt, sendGameplayEvent } from './gameApi'
 import { PendingGameWrites } from './pendingGameWrites'
+import { API_BASE_URL } from './game'
 
 let store: PendingGameWrites | undefined
 
 export function openCollectionStore(): PendingGameWrites {
   store = new PendingGameWrites(localStorage, {
     create: createGameSession, event: sendGameplayEvent, attempt: saveTaskAttempt, complete: completeGameSession,
-  }, (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, ''))
+  }, API_BASE_URL)
   return store
 }
 
diff --git a/frontend/src/main.tsx b/frontend/src/main.tsx
index bef5202..094842a 100644
--- a/frontend/src/main.tsx
+++ b/frontend/src/main.tsx
@@ -1,7 +1,12 @@
 import { StrictMode } from 'react'
 import { createRoot } from 'react-dom/client'
 import './index.css'
-import App from './App.tsx'
+
+// Vite replaces this flag at build time. A collection deployment opens Game
+// directly and does not load the Quiz/Tutor/Avatar application modules.
+const { default: App } = import.meta.env.VITE_GAME_COLLECTION_ONLY === 'true'
+  ? await import('./game/GameCollectionApp.tsx')
+  : await import('./App.tsx')
 
 createRoot(document.getElementById('root')!).render(
   <StrictMode>
diff --git a/frontend/tests/gameCollection.e2e.mjs b/frontend/tests/gameCollection.e2e.mjs
index c4002a1..1694f18 100644
--- a/frontend/tests/gameCollection.e2e.mjs
+++ b/frontend/tests/gameCollection.e2e.mjs
@@ -1,5 +1,7 @@
 /** Synthetic engineering verification only. Requires an explicitly configured
- * isolated loopback API + PostgreSQL. Uses real HTTP; no successful API mocks.
+ * isolated loopback API + local test database and GAME_SYNTHETIC_COLLECTION=true.
+ * PostgreSQL verifies production locking; SQLite verifies HTTP/queue behavior only.
+ * Uses real HTTP; no successful API mocks.
  * GAME_COLLECTION_API=http://127.0.0.1:8137/api/v1 node tests/gameCollection.e2e.mjs
  */
 import assert from 'node:assert/strict'
@@ -12,6 +14,9 @@ import { fileURLToPath } from 'node:url'
 const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
 const api = process.env.GAME_COLLECTION_API
 assert.ok(api && new URL(api).hostname === '127.0.0.1', 'An explicit isolated loopback API is required')
+const targetHealth = await fetch(`${api}/health`, { signal: AbortSignal.timeout(5000) })
+assert.ok(targetHealth.ok && (await targetHealth.json()).synthetic_collection_allowed === true,
+  'Backend must explicitly opt in with GAME_SYNTHETIC_COLLECTION=true and use a local test/synthetic database; no school or remote database is allowed')
 const output = path.join(root, 'artifacts', 'game-collection-' + Date.now())
 const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'game-collection-browser-'))
 const children = [], errors = [], captures = [], sessions = [], actions = [], network = []
@@ -126,7 +131,7 @@ async function until(expression, timeout = 25000) {
 }
 const button = text => `[...document.querySelectorAll('.collection-gate button')].find(b=>b.textContent===${JSON.stringify(text)})`
 async function choose(code) {
-  await until(`document.querySelector('#collection-student') && !document.querySelector('#collection-student').disabled`)
+  await until(`document.querySelector('#collection-student') && !document.querySelector('#collection-student').disabled`, 60000)
   await evaluate(`(() => {const e=document.querySelector('#collection-student');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(code)});e.dispatchEvent(new Event('input',{bubbles:true}));})()`)
   await delay(50)
   await evaluate(`${button('Set student')}.click()`)
@@ -190,7 +195,7 @@ try {
     try { await fetch(`http://127.0.0.1:${port}`, { signal: AbortSignal.timeout(500) }); occupied = true } catch { /* unused */ }
     assert.equal(occupied, false, `Port ${port} already occupied`)
   }
-  const vite = launch(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5197', '--strictPort'], { VITE_API_BASE_URL: api })
+  const vite = launch(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5197', '--strictPort'], { VITE_API_BASE_URL: api, VITE_GAME_COLLECTION_ONLY: 'true' })
   const chrome = launch(process.env.GAME_TEST_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--no-first-run', '--no-default-browser-check', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--remote-allow-origins=*', '--remote-debugging-port=9247', `--user-data-dir=${profile}`, 'about:blank'])
   await Promise.all([ready('http://127.0.0.1:5197', vite), ready('http://127.0.0.1:9247/json', chrome)])
   let page = await connect()
diff --git a/frontend/tests/gameCsvDownload.e2e.mjs b/frontend/tests/gameCsvDownload.e2e.mjs
index b59e3b7..2b7d658 100644
--- a/frontend/tests/gameCsvDownload.e2e.mjs
+++ b/frontend/tests/gameCsvDownload.e2e.mjs
@@ -59,7 +59,7 @@ uvicorn.run(app, host='127.0.0.1', port=8142, access_log=False)
     DATABASE_URL: 'sqlite+pysqlite:///' + path.join(output, 'synthetic-empty.sqlite').replaceAll('\\', '/'),
     GAME_COLLECTION_EXPORT_KEY: key,
   })
-  const vite = launch(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5199', '--strictPort'], frontend, { VITE_API_BASE_URL: api })
+  const vite = launch(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5199', '--strictPort'], frontend, { VITE_API_BASE_URL: api, VITE_GAME_COLLECTION_ONLY: 'true' })
   const chrome = launch(process.env.GAME_TEST_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-allow-origins=*', '--remote-debugging-port=9249', `--user-data-dir=${profile}`, 'about:blank'], frontend)
   await Promise.all([ready(api + '/health', server), ready('http://127.0.0.1:5199', vite), ready('http://127.0.0.1:9249/json', chrome)])
   const targets = await (await fetch('http://127.0.0.1:9249/json')).json()
diff --git a/frontend/vite.config.ts b/frontend/vite.config.ts
index 8b0f57b..78096e2 100644
--- a/frontend/vite.config.ts
+++ b/frontend/vite.config.ts
@@ -1,7 +1,20 @@
-import { defineConfig } from 'vite'
+import { defineConfig, loadEnv } from 'vite'
 import react from '@vitejs/plugin-react'
 
-// https://vite.dev/config/
-export default defineConfig({
-  plugins: [react()],
+export default defineConfig(({ command, mode }) => {
+  const env = loadEnv(mode, process.cwd(), 'VITE_')
+  if (command === 'build') {
+    let api: URL
+    try { api = new URL(env.VITE_API_BASE_URL) }
+    catch { throw new Error('Production builds require VITE_API_BASE_URL=https://<backend-host>/api/v1') }
+    if (api.protocol !== 'https:' || ['localhost', '127.0.0.1', '[::1]'].includes(api.hostname)
+      || api.username || api.password || api.search || api.hash
+      || api.pathname.replace(/\/$/, '') !== '/api/v1') {
+      throw new Error('VITE_API_BASE_URL must be a public HTTPS backend URL ending in /api/v1, without credentials')
+    }
+    if (Object.keys(env).some(key => /SECRET|PASSWORD|PRIVATE|TOKEN|API_KEY|DATABASE/i.test(key))) {
+      throw new Error('Private credentials must never use the public VITE_ prefix')
+    }
+  }
+  return { plugins: [react()] }
 })

diff --git a/backend/app/core/collection_safety.py b/backend/app/core/collection_safety.py
new file mode 100644
--- /dev/null
+++ b/backend/app/core/collection_safety.py
@@ -0,0 +1,18 @@
+"""Synthetic browser runs must not use a local API backed by a remote DB."""
+
+from sqlalchemy.engine import make_url
+
+
+def synthetic_collection_allowed(database_url: str, opted_in: bool) -> bool:
+    if not opted_in:
+        return False
+    try:
+        url = make_url(database_url)
+        name = (url.database or "").lower()
+        return (
+            url.get_backend_name() in {"sqlite", "postgresql"}
+            and (url.get_backend_name() == "sqlite" or url.host in {"localhost", "127.0.0.1", "::1"})
+            and ("synthetic" in name or "test" in name)
+        )
+    except Exception:
+        return False

diff --git a/backend/app/core/game_deployment.py b/backend/app/core/game_deployment.py
new file mode 100644
--- /dev/null
+++ b/backend/app/core/game_deployment.py
@@ -0,0 +1,66 @@
+"""Shared Railway app safeguards; no student authentication protocol."""
+
+import os
+from collections.abc import Mapping
+from ipaddress import ip_address
+from urllib.parse import urlsplit
+
+from fastapi import HTTPException
+
+
+def is_hosted_runtime(environment: Mapping[str, str] | None = None) -> bool:
+    environment = os.environ if environment is None else environment
+    # Railway injects these IDs. No new Railway variable is required.
+    return bool(
+        environment.get("RAILWAY_ENVIRONMENT_ID")
+        or environment.get("RAILWAY_SERVICE_ID")
+        or environment.get("GAME_DEPLOYMENT_ENV") == "production"
+    )
+
+
+def validate_https_origin(origin: str) -> str:
+    try:
+        url = urlsplit(origin)
+        host = (url.hostname or "").lower().rstrip(".")
+        local = host == "localhost" or host.endswith(".localhost")
+        try:
+            address = ip_address(host)
+            local = local or address.is_loopback or address.is_unspecified
+        except ValueError:
+            pass
+        _ = url.port
+        valid = (
+            url.scheme == "https" and host and not local
+            and not url.username and not url.password and not url.path
+            and not url.query and not url.fragment and "*" not in origin
+        )
+    except ValueError:
+        valid = False
+    if not valid:
+        raise ValueError("CORS origins must be exact HTTPS origins without paths, credentials or wildcards")
+    return origin
+
+
+def configured_cors_origins(frontend_url: str, additional: list[str], hosted: bool) -> list[str]:
+    origins = list(additional)
+    if hosted:
+        try:
+            origins.insert(0, validate_https_origin(frontend_url))
+        except ValueError:
+            # Ignore the development default without crashing other modules.
+            pass
+    else:
+        origins.insert(0, frontend_url)
+    return list(dict.fromkeys(origins))
+
+
+def require_approved_collection_access() -> None:
+    """Keep hosted Game data closed until approved authorization AND verification.
+
+    No shared browser key, learner code or environment toggle unlocks access.
+    Implement the reviewed approach separately before releasing collection.
+    """
+    raise HTTPException(
+        503, "School collection is unavailable until approved access control is configured.",
+        headers={"Cache-Control": "no-store"},
+    )

diff --git a/backend/tests/test_game_deployment.py b/backend/tests/test_game_deployment.py
new file mode 100644
--- /dev/null
+++ b/backend/tests/test_game_deployment.py
@@ -0,0 +1,126 @@
+"""Shared Railway perimeter tests; no remote database connections."""
+
+import pytest
+from fastapi.testclient import TestClient
+from pydantic import ValidationError
+
+from app.core.collection_safety import synthetic_collection_allowed
+from app.core.config import Settings
+from app.core.game_deployment import configured_cors_origins, is_hosted_runtime
+from app.db.session import get_db
+from app.main import create_app
+
+
+def configuration(**changes):
+    return Settings(_env_file=None, **{
+        "database_url": "sqlite+pysqlite:///:memory:",
+        "frontend_url": "https://existing-team.example",
+        "cors_origins": ["https://approved-vercel.example"],
+        **changes,
+    })
+
+
+@pytest.mark.parametrize("origin", [
+    "*", "https://*.example", "http://approved.example", "https://localhost",
+    "https://127.0.0.2", "https://[::1]", "https://approved.example/path",
+    "https://approved.example/", "https://user:password@approved.example",
+    "https://approved.example:bad",
+])
+def test_additional_cors_origins_must_be_exact_https(origin):
+    with pytest.raises(ValidationError):
+        configuration(cors_origins=[origin])
+
+
+@pytest.mark.parametrize(("environment", "expected"), [
+    ({}, False),
+    ({"GAME_DEPLOYMENT_ENV": "development"}, False),
+    ({"GAME_DEPLOYMENT_ENV": "production"}, True),
+    ({"RAILWAY_ENVIRONMENT_ID": "synthetic-environment"}, True),
+    ({"RAILWAY_SERVICE_ID": "synthetic-service"}, True),
+    ({"RAILWAY_ENVIRONMENT_ID": "synthetic-environment", "GAME_DEPLOYMENT_ENV": "development"}, True),
+])
+def test_railway_ids_keep_game_blocked_without_new_environment_settings(environment, expected):
+    assert is_hosted_runtime(environment) is expected
+
+
+@pytest.fixture
+def client(monkeypatch):
+    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "synthetic-environment")
+    app = create_app(configuration())
+
+    def forbidden_database_access():
+        pytest.fail("Blocked deployment request reached the database")
+
+    app.dependency_overrides[get_db] = forbidden_database_access
+    return TestClient(app)
+
+
+@pytest.mark.parametrize(("method", "path"), [
+    ("POST", "/game/sessions"), ("POST", "/game/events"),
+    ("POST", "/game/task-attempts"), ("POST", "/game/sessions/known-session/complete"),
+    ("GET", "/game/results/known-session"),
+    ("GET", "/game/variant-usage?student_id=STU_001&concept_id=linear_equations"),
+    ("GET", "/game/exports/collection"),
+])
+def test_shared_railway_app_blocks_game_before_database_access(client, method, path):
+    response = client.request(method, "/api/v1" + path)
+    assert response.status_code == 503
+    assert response.headers["cache-control"] == "no-store"
+    assert client.request(method, "/api/v1" + path, headers={"Authorization": "Bearer synthetic-only"}).status_code == 503
+
+
+def test_shared_modules_and_route_paths_are_preserved(monkeypatch):
+    for key in ("RAILWAY_ENVIRONMENT_ID", "RAILWAY_SERVICE_ID", "GAME_DEPLOYMENT_ENV"):
+        monkeypatch.delenv(key, raising=False)
+    local = create_app(configuration()).openapi()["paths"]
+    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "synthetic-environment")
+    hosted = create_app(configuration()).openapi()["paths"]
+    assert set(hosted) == set(local)
+    for module in ("game", "quiz", "tutor"):
+        assert any(path.startswith(f"/api/v1/{module}/") for path in hosted)
+
+
+def test_shared_health_is_liveness_only_and_simulator_is_never_enabled_on_railway(client, monkeypatch):
+    from app.db.session import engine
+
+    def forbidden_connect(*args, **kwargs):
+        pytest.fail("Liveness queried the database")
+
+    monkeypatch.setattr(engine, "connect", forbidden_connect)
+    monkeypatch.setenv("GAME_SYNTHETIC_COLLECTION", "true")
+    assert client.get("/api/v1/health").json() == {
+        "status": "ok", "service": "sign-supported-ai-tutor-api",
+        "synthetic_collection_allowed": False,
+    }
+
+
+def test_hosted_cors_preserves_existing_origin_and_accepts_additional_vercel_origin(client):
+    for origin, status in [
+        ("https://existing-team.example", 200), ("https://approved-vercel.example", 200),
+        ("http://localhost:5173", 400), ("https://unapproved.example", 400),
+    ]:
+        response = client.options("/api/v1/game/sessions", headers={
+            "Origin": origin, "Access-Control-Request-Method": "POST",
+            "Access-Control-Request-Headers": "content-type",
+        })
+        assert response.status_code == status
+        assert (response.headers.get("access-control-allow-origin") == origin) == (status == 200)
+
+
+def test_development_default_is_not_allowed_as_a_hosted_origin():
+    assert configured_cors_origins("http://localhost:5173", [], hosted=True) == []
+    assert configured_cors_origins("http://localhost:5173", [], hosted=False) == ["http://localhost:5173"]
+    assert configured_cors_origins("https://team.example", ["https://team.example"], hosted=True) == ["https://team.example"]
+
+
+@pytest.mark.parametrize(("url", "opted_in", "expected"), [
+    ("sqlite+pysqlite:///synthetic-only.sqlite", True, True),
+    ("sqlite+pysqlite:///school.sqlite", True, False),
+    ("sqlite+pysqlite:///synthetic-only.sqlite", False, False),
+    ("postgresql+psycopg://unused@127.0.0.1/game_synthetic", True, True),
+    ("postgresql+psycopg://unused@127.0.0.1/school", True, False),
+    ("postgresql+psycopg://unused@db.invalid/game_synthetic", True, False),
+    ("invalid", True, False),
+])
+def test_synthetic_browser_permission_requires_local_isolated_database(url, opted_in, expected):
+    assert synthetic_collection_allowed(url, opted_in) is expected

diff --git a/frontend/.env.example b/frontend/.env.example
new file mode 100644
--- /dev/null
+++ b/frontend/.env.example
@@ -0,0 +1,6 @@
+# Vercel Production build settings only; public URL supplied by the owner.
+# Local gameplay tests must override this with an isolated loopback API.
+VITE_API_BASE_URL=https://backend-production-b489d.up.railway.app/api/v1
+# Dedicated teacher Game entry; production collection remains blocked in code.
+VITE_GAME_COLLECTION_ONLY=false
+# Never add database credentials, researcher keys or staff tokens as VITE_* variables.

diff --git a/frontend/src/game/CollectionUnavailable.tsx b/frontend/src/game/CollectionUnavailable.tsx
new file mode 100644
--- /dev/null
+++ b/frontend/src/game/CollectionUnavailable.tsx
@@ -0,0 +1,10 @@
+import './CollectionGate.css'
+
+export function CollectionUnavailable() {
+  return <div className="collection-shell">
+    <section className="collection-gate" aria-label="School collection unavailable">
+      <h1>School collection is not available yet</h1>
+      <p>Your teacher or researcher will provide access when collection is ready.</p>
+    </section>
+  </div>
+}

diff --git a/frontend/src/game/GameCollectionApp.tsx b/frontend/src/game/GameCollectionApp.tsx
new file mode 100644
--- /dev/null
+++ b/frontend/src/game/GameCollectionApp.tsx
@@ -0,0 +1,16 @@
+import { PhaserGame } from './phaser/PhaserGame'
+import '../App.css'
+
+// Hosting entry uses the existing collection gate and both existing games.
+// The normal team application remains available in development builds.
+export default function GameCollectionApp() {
+  return <>
+    <nav className="app-navigation" aria-label="Learning tools">
+      <span className="app-navigation-title">
+        <img className="app-navigation-logo" src="/connected-learning-emblem.png" alt="" width="48" height="48" />
+        Sign &amp; Learn · Equation Game
+      </span>
+    </nav>
+    <main className="game-page"><PhaserGame /></main>
+  </>
+}

diff --git a/frontend/tests/gameCollectionRecovery.test.ts b/frontend/tests/gameCollectionRecovery.test.ts
new file mode 100644
--- /dev/null
+++ b/frontend/tests/gameCollectionRecovery.test.ts
@@ -0,0 +1,69 @@
+import assert from 'node:assert/strict'
+import test from 'node:test'
+import { PendingGameWrites } from '../src/game/api/pendingGameWrites.ts'
+import type { CollectionTransport } from '../src/game/api/pendingGameWrites.ts'
+
+const destination = 'https://synthetic-api.example/api/v1'
+function storage() {
+  const values = new Map<string, string>()
+  return { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value) } }
+}
+function learner(student_id: string) {
+  return { student_id, client_session_id: crypto.randomUUID(), concept_id: 'linear_equations', learning_cycle_id: crypto.randomUUID(), assessment_phase: 'pre_tutor' as const }
+}
+
+test('Game preserves exact evidence after response loss and reopen, then permits a different learner', async () => {
+  const local = storage()
+  const received = new Map<string, unknown>()
+  let loseResponse = true
+  const transport: CollectionTransport = {
+    create: async input => ({ game_session_id: input.client_session_id!, student_id: input.student_id }),
+    event: async input => {
+      received.set(String(input.event_payload?.client_event_id), structuredClone(input))
+      if (loseResponse) throw Error('Response lost after persistence')
+    },
+    attempt: async () => {}, complete: async id => ({ game_session_id: id, status: 'completed' }),
+  }
+  const first = learner('STU_001'), second = learner('STU_002')
+  const initial = new PendingGameWrites(local, transport, destination)
+  initial.start(first, 'hangman')
+  initial.event(first.client_session_id, { event_type: 'ANSWER_CORRECT', event_timestamp: new Date().toISOString(), event_payload: { submitted_value: '4' } })
+  const original = initial.session(first.client_session_id).writes
+  assert.equal(await initial.flush(first.client_session_id), false)
+  assert.equal(initial.status(first.client_session_id), 'Failed')
+  assert.throws(() => initial.close(first.client_session_id))
+  assert.throws(() => initial.start(second, 'drag_drop'))
+  const reopened = new PendingGameWrites(local, transport, destination)
+  assert.deepEqual(reopened.session(first.client_session_id).writes, original)
+  assert.throws(() => new PendingGameWrites(local, transport, 'https://different.example/api/v1'))
+  loseResponse = false
+  assert.equal(await reopened.flush(first.client_session_id), true)
+  assert.equal(received.size, 2, 'the response-loss retry retained its event identity')
+  assert.equal(reopened.status(first.client_session_id), 'Saved')
+  assert.equal(reopened.session(first.client_session_id).completed, false, 'Saved is not assessment completion')
+  reopened.close(first.client_session_id)
+  reopened.start(second, 'drag_drop')
+  assert.notEqual(first.client_session_id, second.client_session_id)
+  assert.equal(reopened.session(second.client_session_id).request.student_id, 'STU_002')
+  assert.equal(reopened.session(first.client_session_id).request.student_id, 'STU_001')
+})
+
+test('Separate device stores can flush concurrently with distinct sessions and learners', async () => {
+  const recorded = new Map<string, string>()
+  const transport: CollectionTransport = {
+    create: async input => {
+      recorded.set(input.client_session_id!, input.student_id)
+      return { game_session_id: input.client_session_id!, student_id: input.student_id }
+    }, event: async () => {}, attempt: async () => {},
+    complete: async id => ({ game_session_id: id, status: 'completed' }),
+  }
+  const first = learner('STU_001'), second = learner('STU_002')
+  const deviceA = new PendingGameWrites(storage(), transport, destination)
+  const deviceB = new PendingGameWrites(storage(), transport, destination)
+  deviceA.start(first, 'drag_drop'); deviceB.start(second, 'hangman')
+  assert.deepEqual(await Promise.all([deviceA.flush(first.client_session_id), deviceB.flush(second.client_session_id)]), [true, true])
+  assert.equal(recorded.get(first.client_session_id), 'STU_001')
+  assert.equal(recorded.get(second.client_session_id), 'STU_002')
+  assert.equal(deviceA.sessions().length, 1)
+  assert.equal(deviceB.sessions().length, 1)
+})

diff --git a/frontend/tests/gameProductionGate.e2e.mjs b/frontend/tests/gameProductionGate.e2e.mjs
new file mode 100644
--- /dev/null
+++ b/frontend/tests/gameProductionGate.e2e.mjs
@@ -0,0 +1,93 @@
+/** Production preview only. Every hosted API request is intercepted and aborted.
+ * Build with VITE_GAME_COLLECTION_ONLY=true, then run this script from frontend/.
+ * No Game writes, backend process or database is used.
+ */
+import assert from 'node:assert/strict'
+import { spawn } from 'node:child_process'
+import fs from 'node:fs/promises'
+import os from 'node:os'
+import path from 'node:path'
+import { fileURLToPath } from 'node:url'
+
+const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
+const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'game-production-block-'))
+const children = [], apiRequests = []
+const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
+let socket
+function launch(command, args) {
+  const child = spawn(command, args, { cwd: root, stdio: 'ignore', windowsHide: true })
+  children.push(child)
+  return child
+}
+async function ready(url, child) {
+  for (let n = 0; n < 200; n++) {
+    if (child.exitCode !== null) throw Error('Test process exited: ' + url)
+    try { if ((await fetch(url, { signal: AbortSignal.timeout(500) })).ok) return } catch { /* startup */ }
+    await delay(100)
+  }
+  throw Error('Startup timeout: ' + url)
+}
+
+try {
+  for (const port of [5201, 9251]) {
+    let occupied = false
+    try { await fetch(`http://127.0.0.1:${port}`, { signal: AbortSignal.timeout(500) }); occupied = true } catch { /* unused */ }
+    assert.equal(occupied, false, `Port ${port} is occupied`)
+  }
+  const vite = launch(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1', '--port', '5201', '--strictPort'])
+  const chrome = launch(process.env.GAME_TEST_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-allow-origins=*', '--remote-debugging-port=9251', `--user-data-dir=${profile}`, 'about:blank'])
+  await Promise.all([ready('http://127.0.0.1:5201', vite), ready('http://127.0.0.1:9251/json', chrome)])
+  const targets = await (await fetch('http://127.0.0.1:9251/json')).json()
+  socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl)
+  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }) })
+  let id = 0
+  const pending = new Map()
+  const send = (method, params = {}) => new Promise((resolve, reject) => {
+    const next = ++id
+    const timer = setTimeout(() => { pending.delete(next); reject(Error('CDP timeout: ' + method)) }, 15000)
+    pending.set(next, { resolve, reject, timer })
+    socket.send(JSON.stringify({ id: next, method, params }))
+  })
+  socket.addEventListener('close', () => {
+    for (const p of pending.values()) { clearTimeout(p.timer); p.reject(Error('Browser closed')) }
+    pending.clear()
+  })
+  socket.addEventListener('message', event => {
+    const message = JSON.parse(event.data)
+    if (message.method === 'Fetch.requestPaused') {
+      apiRequests.push(message.params.request.url)
+      void send('Fetch.failRequest', { requestId: message.params.requestId, errorReason: 'BlockedByClient' })
+      return
+    }
+    const p = pending.get(message.id)
+    if (!p) return
+    clearTimeout(p.timer); pending.delete(message.id)
+    if (message.error) p.reject(Error(JSON.stringify(message.error)))
+    else p.resolve(message.result)
+  })
+  const evaluate = async expression => {
+    const result = await send('Runtime.evaluate', { expression, returnByValue: true })
+    if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails))
+    return result.result.value
+  }
+  await send('Page.enable')
+  await send('Fetch.enable', { patterns: [{ urlPattern: '*://*/api/v1/*', requestStage: 'Request' }] })
+  await send('Page.addScriptToEvaluateOnNewDocument', { source: "localStorage.setItem('game.collection.pending.v1', 'synthetic-evidence-do-not-clear');" })
+  await send('Page.navigate', { url: 'http://127.0.0.1:5201' })
+  let blocked = false
+  for (let n = 0; n < 600; n++) {
+    blocked = await evaluate("!!document.querySelector('[aria-label=\"School collection unavailable\"]')")
+    if (blocked) break
+    await delay(100)
+  }
+  assert.equal(blocked, true, 'Production must show the unavailable screen')
+  assert.equal(await evaluate("!!document.querySelector('#collection-student, canvas, .collection-export')"), false)
+  assert.equal(await evaluate("localStorage.getItem('game.collection.pending.v1')"), 'synthetic-evidence-do-not-clear')
+  await evaluate("window.dispatchEvent(new Event('online'))")
+  await delay(1000)
+  assert.deepEqual(apiRequests, [], 'Production collection attempted an API request')
+  console.log('PASS production collection blocked: no learner controls, canvas, API requests or storage recovery/clearing')
+} finally {
+  socket?.close()
+  for (const child of children) child.kill('SIGTERM')
+}

diff --git a/frontend/vercel.json b/frontend/vercel.json
new file mode 100644
--- /dev/null
+++ b/frontend/vercel.json
@@ -0,0 +1,18 @@
+{
+  "$schema": "https://openapi.vercel.sh/vercel.json",
+  "framework": "vite",
+  "installCommand": "npm ci",
+  "buildCommand": "npm run build",
+  "outputDirectory": "dist",
+  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }],
+  "headers": [
+    {
+      "source": "/(.*)",
+      "headers": [
+        { "key": "X-Content-Type-Options", "value": "nosniff" },
+        { "key": "Referrer-Policy", "value": "no-referrer" },
+        { "key": "X-Robots-Tag", "value": "noindex, nofollow" }
+      ]
+    }
+  ]
+}

diff --git a/docs/GAME_ACCESS_CONTROL_PROPOSAL.md b/docs/GAME_ACCESS_CONTROL_PROPOSAL.md
new file mode 100644
--- /dev/null
+++ b/docs/GAME_ACCESS_CONTROL_PROPOSAL.md
@@ -0,0 +1,147 @@
+# PP1 teacher-controlled access proposal — review required
+
+**Proposal only. Not implemented, approved, enabled or deployed.**
+The owner confirmed on October 16, 2026 that there is no approved student authentication
+service or school sign-in integration. Students must not need individual accounts.
+An authorized teacher/researcher selects the approved learner code and supervises play.
+Production recording remains blocked in the prepared Railway Game dependency
+`require_approved_collection_access` and independently in the production frontend.
+The existing Railway service is not changed by local source edits. Keep the shared
+`app.main:app` and its Quiz/Tutor routes; review cross-module access to Game records
+as part of authorization rather than replacing the backend with a Game-only service.
+
+## Existing mechanisms inspected
+
+| Mechanism | Reusable part | Limitation |
+| --- | --- | --- |
+| `backend/app/modules/game/collection_export.py` | FastAPI bearer dependency, secret configuration, constant-time credential comparison, fail-closed export checks | One static collection-wide researcher key; no login, roles, expiry, revocation per operator, code scope or session ownership |
+| `backend/app/modules/quiz/collection_export.py` | Same narrow export-key pattern | Quiz-specific; no shared authentication service; leave Quiz logic unchanged |
+| `frontend/src/game/collectionIdentity.ts` | Assigned-code validation and explicit active code | Identifier only; client state can be changed by callers |
+| `frontend/src/game/identity.ts` | Legacy local pseudonymous identity | Explicitly has no login system; not authentication |
+| Game pending store and backend retry IDs | Preserve original code/session/event identities during retries | Identity consistency is not an access grant |
+| CORS and research-verification CSVs | Origin restrictions and research evidence review | Neither authenticates an HTTP caller |
+
+Searches covered backend application modules, frontend source, dependency manifests,
+environment examples and deployment configuration. No staff login, session-cookie
+middleware, Supabase Auth client, JWT verification, OAuth integration or authorization
+ownership store was found. The Tutor OpenAI authorization header authenticates an
+outbound OpenAI request; it grants no access to this application. No hosting account
+or Supabase Auth configuration was inspected, so the findings concern this repository.
+
+Reuse the dependency structure and denial/error handling, rather than broadening the
+export key into a classroom login. Do not give students a staff/researcher bearer key.
+
+## Recommended minimum
+
+Use **managed Supabase Auth for invited staff only**, subject to project-owner and
+research approval, plus ordinary backend-managed web sessions with an active
+collection scope. There are no student accounts. This is the recommended new service
+for review, not a claim that existing Supabase database approval includes Auth approval.
+If Supabase Auth is not approved, choose a reviewed managed staff identity service;
+do not implement a password database or a bespoke JWT protocol for PP1.
+
+Supabase supplies staff credential verification and JWTs; the backend must validate
+the provider identity using its supported SDK or a maintained verifier (signature,
+issuer, audience, expiry), then check a **server-owned allowlist of immutable staff
+user IDs** with `collector` or `researcher` permissions. Do not trust a browser role,
+email domain alone, or user-editable metadata. Invited accounts alone do not replace
+this authorization check. Review shared-project impacts before changing any global
+Auth settings; this project may be shared with other modules.
+
+Keep provider refresh/access tokens server-side. Use established web-session tooling
+with opaque, unpredictable session identifiers in Secure, HttpOnly cookies; rotate
+the session on login and privilege changes, enforce idle/absolute expiry, logout and
+revocation, and add CSRF protection for state-changing cookie-authenticated requests.
+Do not put staff tokens in localStorage, URLs or the Game evidence queue.
+
+The session store tracks two server-enforced modes:
+
+1. **Staff setup:** freshly authenticated teacher/researcher selects one assigned code
+   from the separately approved consent/code assignment. The backend checks the staff
+   member's collection scope. There is no browser roster download or student names.
+2. **Student play:** before handoff, the backend locks that browser session to the
+   selected code, concept, permitted games and newly granted Game session IDs. It
+   disables staff administration/export privileges in that session. The learner can
+   use the existing Game UI without an account. Switching codes, expanding scope or
+   returning to staff controls requires fresh teacher authentication, not a client
+   checkbox, a recent JWT timestamp or merely presenting the old browser cookie.
+
+Research downloads use a separately authenticated researcher session on a researcher
+device. A collector has no collection-wide export permission. If a researcher also
+supervises student play, that school's browser must be locked to collection mode
+before handoff; their researcher role must not remain callable from that browser.
+Researcher read/export authorization must be checked server-side on every request.
+
+This lock is necessary: signing a teacher in and leaving their full credentials or
+privileges active while a student plays permits the student to use those privileges.
+A frontend-hidden download button would not solve that problem.
+
+## Access store and API requirements
+
+Persist small staff-session/collection-grant records in a reviewed shared session store
+so Railway restart, expiry and multiple workers do not lose the authorization mapping.
+Store the operator's provider ID, authorized code, granted existing Game session IDs,
+mode, expiry and revocation state. A separate access-control schema/table or an
+approved managed session store requires explicit design/storage approval. Do not
+alter the Game tables, add a student registry, rename session IDs or automatically
+apply a migration. In-memory dictionaries alone are insufficient for durable recovery.
+
+For every session/event/attempt/completion/result request, verify the authenticated
+browser session and active grant, load the referenced Game session, and check its
+recorded code and granted ID match the scope. Never infer permission from a UUID or
+code supplied by the caller. Check creation/replay ownership before returning an
+existing session; create the authorization mapping safely with session creation so
+an acknowledgement loss cannot assign another caller's session to the current grant.
+
+`variant-usage` may serve only the active approved code/concept's limited counts;
+changing a query parameter cannot reveal another learner's history. Results may
+serve only the current granted Game sessions during student play. Broader historical
+reads and exports require the separately authenticated researcher permission and
+approved collection scope. Do not create roster/history APIs for students.
+
+After browser reopening or login expiry, the teacher reauthenticates and restores
+the prior authorized grant for the original learner/session. Retry the existing
+payloads and IDs unchanged. A new active learner cannot flush another learner's
+queue. Logout/revocation blocks requests without deleting evidence. Define how a
+designated researcher recovers a prior operator's pending collection under approval.
+
+Use per-operator/device grants: several school devices may collect concurrently,
+without one shared global active-code variable. Apply login/request rate limits,
+restricted audit logs of access decisions, and no answer bodies or secrets in logs.
+Teacher consent confirmation and a reviewed code assignment remain necessary;
+authenticating staff alone cannot establish learner consent.
+
+## Domain/cookie decision before implementation
+
+The Vercel frontend and existing `up.railway.app` backend use different sites. Do not assume
+cross-site cookies will work on managed school browsers. Prefer an approved same-site
+custom-domain pair or a reviewed same-origin backend proxy. Decide this before adding
+login/session routes. For a cookie-based cross-origin API, exact-origin credential
+CORS, browser `credentials` handling, cookie attributes and CSRF defenses need coordinated
+changes. The prepared shared backend retains credential CORS for exact approved
+origins and has no proxy. That CORS setting alone does not implement cookie sessions,
+authentication, CSRF protection or this proposal. The eventual Vercel domain is
+still unknown; no Railway environment variables or provider settings have changed.
+
+## Approval and acceptance
+
+Review and approve the staff identity provider/account provisioning, collector/researcher
+roles and scopes, browser handoff lock/reauthentication, persistent access store,
+domain/cookie/CSRF design, recovery/expiry/revocation, and retention/audit rules. Only
+then implement the approved approach in a separate change. Nothing in this proposal
+creates users, changes shared Supabase settings, changes data or enables recording.
+
+Required tests include missing/invalid/expired login, direct API requests, collector
+export denial, locked-browser attempts to regain staff privileges, another-code and
+another-session denial, session-creation replay conflicts, two independent device
+grants, refresh/tab-close recovery after reauthentication, revocation, API restart,
+and CSRF/origin enforcement. Repeat recording tests against an isolated PostgreSQL
+database and complete the hosted release checklist only with explicit authorization.
+
+Sources supporting the standard components: [Supabase Auth](https://supabase.com/docs/guides/auth),
+[JWT verification](https://supabase.com/docs/guides/auth/jwts),
+[admin-created users](https://supabase.com/docs/reference/javascript/auth-admin-createuser),
+[OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
+[OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
+The staff/collection lock and access-store requirements are architectural recommendations
+for this application's supervised handoff; the sources do not implement them here.

diff --git a/docs/GAME_DEPLOYMENT.md b/docs/GAME_DEPLOYMENT.md
new file mode 100644
--- /dev/null
+++ b/docs/GAME_DEPLOYMENT.md
@@ -0,0 +1,326 @@
+# PP1 Game website deployment preparation — October 16, 2026
+
+**Existing backend: Railway (owner confirmed). Vercel frontend: NOT DEPLOYED.**
+**Vercel → Railway → Supabase recording: NOT VERIFIED. Student collection: BLOCKED.**
+Target date: October 22, 2026. This correction prepares local files only. No hosting account,
+remote database, migration, commit, push, merge or branch switch is authorized.
+Do not share a school collection link until every release prerequisite below is met.
+
+## What needs hosting
+
+| Component | Deployment |
+| --- | --- |
+| React/Vite/Phaser Game client | Vercel, project root `frontend`, build `npm run build`, output `dist` |
+| Shared FastAPI API | Existing Railway service, backend root `backend`, retain `app.main:app` and Game/Quiz/Tutor routes |
+| Existing PostgreSQL Game tables | Existing authorized Supabase project; no new database or schema reset |
+| Research exports/ML training | Restricted researcher environment; not required on student computers |
+
+Owner-supplied public backend origin: `https://backend-production-b489d.up.railway.app`.
+The frontend API base is exactly `https://backend-production-b489d.up.railway.app/api/v1`.
+The Vercel production domain has not been selected. No replacement backend service is
+needed. The superseded `render.yaml` and Game-only backend entry were removed locally;
+no hosting resources were created or deleted. Existing Railway account settings and
+deployed revision were not inspected or changed.
+
+The inspected branch is `feature_game-modal_v1`. It already contains uncommitted
+Game visuals and ML/research work, including Milestone 2.2 and session verification.
+Those changes are preserved. A hosting provider can only build an owner-approved
+remote revision; the current local preparation is not available there automatically.
+Do not deploy an older remote revision while assuming these safeguards are present.
+
+The normal frontend uses React state to switch views, rather than React Router.
+The dedicated collection build selects the existing Game entry. For now its production
+gate shows an unavailable screen: no learner entry, Game canvas, export controls,
+pending-evidence recovery or Game HTTP requests. Both games remain available for
+isolated local development verification. `frontend/vercel.json` supplies an SPA fallback.
+Quiz/Tutor/Avatar/Remedial business logic and Game scoring/classifications are untouched.
+
+## Blocking access-control decision
+
+`STU_001` is a pseudonymous identifier. Format validation and the teacher's visual
+code check do not authenticate a learner, verify consent, or authorize API access.
+The owner confirmed that no student/school authentication service is currently approved.
+Students should use a teacher-controlled flow without individual accounts. There is
+no approved staff authentication/session authorization implementation in this checkout.
+CORS, an unguessable UUID, Vercel page protection, and hiding a link cannot replace it:
+the Railway API is separately reachable.
+
+The prepared shared `app.main:app` detects Railway's injected environment/service IDs
+and applies `require_approved_collection_access` before database dependencies on
+**every direct Game endpoint**. All return HTTP 503 until approved
+authorization is implemented, including requests with an export key. There is no
+environment switch to enable anonymous collection. The production frontend also
+blocks the Game collection gate independently, because local backend changes do not
+protect the revision already running on Railway. Existing pending storage is left
+untouched and is not flushed from the blocked frontend.
+The health endpoint's HTTP 200 proves liveness only, not recording readiness.
+
+The shared entry no longer refuses production startup or drops Quiz/Tutor routes.
+Local development retains normal Game behavior; Railway remains blocked even if
+`GAME_DEPLOYMENT_ENV=development` is supplied. No new Railway variable is needed for
+detection. The legacy explicit `GAME_DEPLOYMENT_ENV=production` also blocks Game when
+testing hosted behavior outside Railway. These source safeguards have not been deployed.
+Do not claim the live API is secured by this local correction. Other shared routes,
+including any cross-module access to Game records, need review before release; the
+direct Game gate is not a complete authorization solution for the shared backend.
+
+| Existing Game endpoint | Authorization required before release |
+| --- | --- |
+| `POST /api/v1/game/sessions` | Authenticated teacher/researcher collection grant for the approved code and consent; replay must belong to that grant |
+| `POST /api/v1/game/events` | Ownership of the referenced session, including replayed pending events |
+| `POST /api/v1/game/task-attempts` | Ownership of the referenced session and its attempts |
+| `POST /api/v1/game/sessions/{id}/complete` | Session ownership; knowledge of ID is insufficient |
+| `GET /api/v1/game/results/{id}` | Active collection grant's result or separately authorized researcher role |
+| `GET /api/v1/game/variant-usage?student_id=...&concept_id=...` | Learner-scoped history; reject another learner's code |
+| `GET /api/v1/game/exports/collection` | Researcher authorization; returns collection-wide answers/events/analytics |
+
+The export route already checks a backend-only bearer export key (minimum 16
+characters), fails closed when unconfigured, and sends `Cache-Control: no-store`.
+That key has no expiry, individual identity, or learner scope. It is not a student
+login solution and must never be placed in `VITE_*`, source code or a shared school
+browser. Production's additional gate currently also blocks this endpoint.
+
+The repository has only narrow Game/Quiz researcher export-key checks, not a reusable
+staff login or session authorization system. The recommended minimal design is
+managed **staff-only Supabase Auth**, backend web sessions, and a per-device collection
+grant locked to the selected code and Game sessions before student handoff. No student
+accounts are needed. Full staff privileges must not remain available in the student's
+browser. See [GAME_ACCESS_CONTROL_PROPOSAL.md](GAME_ACCESS_CONTROL_PROPOSAL.md) for the
+inspection findings, scope/recovery/domain decisions and acceptance tests. This is a
+proposal for review, not implemented authentication. Do not create accounts, change
+Supabase Auth settings, add access tables, or unlock production recording before approval.
+
+## Environment variables
+
+Set real credentials through provider environment settings only. The placeholders
+below contain no account-specific values. Do not copy the root `.env` to Vercel.
+The existing backend settings convention is preserved: real environment variables
+override the repository-root `.env`. No live environment values were changed.
+
+| Name | Where | Required/value |
+| --- | --- | --- |
+| `DATABASE_URL` | Existing Railway secret | Preserve the existing authorized Supabase connection; do not replace, print or change it |
+| `FRONTEND_URL` | Existing Railway setting | Preserve the existing approved origin; inspect its value before proposing any change |
+| `CORS_ORIGINS` | Optional proposed Railway setting | Additive JSON array of exact approved HTTPS origins; use the eventual Vercel domain, not a wildcard or path |
+| `PORT` | Railway platform | Use the existing service's supplied port; do not manually change it |
+| `RAILWAY_ENVIRONMENT_ID`, `RAILWAY_SERVICE_ID` | Railway platform | Automatic hosted detection; do not add, clear or override these IDs |
+| `GAME_DEPLOYMENT_ENV` | Optional local hosted-mode test | `production` blocks Game outside Railway; not a required new Railway variable |
+| `VITE_API_BASE_URL` | Vercel Production build | `https://backend-production-b489d.up.railway.app/api/v1` |
+| `VITE_GAME_COLLECTION_ONLY` | Vercel Production build | `true`; dedicated Game entry, currently blocked in production |
+| `GAME_COLLECTION_EXPORT_KEY` | Researcher backend only | Existing export mechanism; optional and insufficient to unlock production access |
+| `GAME_SYNTHETIC_COLLECTION` | Isolated local test server only | `true` opts into the simulator's target handshake; never set on school/production services |
+| `GAME_COLLECTION_API` | Local browser test process only | Explicit loopback synthetic API; never the hosted service |
+| `GAME_COLLECTION_TEST_DATABASE_URL` | Opt-in PostgreSQL test only | Dedicated disposable local PostgreSQL database; never the authorized school DB |
+
+`FRONTEND_PORT` and `BACKEND_PORT` remain development settings. `FRONTEND_URL` remains
+supported by the shared service. Optional `CORS_ORIGINS` adds exact HTTPS origins to
+it, rather than removing an existing team frontend. On Railway, the prepared code
+disables the development localhost regex and ignores a localhost/HTTP `FRONTEND_URL`
+default. If no approved HTTPS origin is configured, browser CORS stays closed without
+crashing Quiz/Tutor. Existing credential-CORS behavior is retained for exact origins;
+it does not authenticate callers or enable collection.
+OpenAI keys, Supabase service-role keys and database passwords are not frontend settings
+and are unnecessary in the Game frontend. Preserve any existing backend Tutor keys
+and RAG settings. Do not add analytics/error-recording tools
+that capture answers or codes without approval. Do not log request bodies or credentials.
+
+The Vite build rejects missing API URLs, HTTP/localhost URLs, credentials in URLs,
+incorrect API paths, and common secret-bearing `VITE_*` names. The Game transport and
+pending store share the same normalized API URL. Changing it on an existing browser
+profile triggers destination mismatch protection; pending evidence is not redirected.
+Vite variables are embedded at build time; changing a Vercel variable requires rebuilding.
+
+## Database compatibility and isolation
+
+No models, migrations, scoring code or session ID formats change here. Existing
+`game_sessions`, `gameplay_events`, `game_task_attempts`, and `game_results` are used.
+The backend persists through SQLAlchemy/psycopg; the browser never connects to Postgres.
+Client-created session IDs remain UUID strings, as do retry keys and learning-cycle IDs.
+
+Before an authorized deployment, have the database owner perform a read-only check of
+the actual Game columns, UUID/time-zone/JSONB types, unique session IDs, foreign keys,
+attempt keys and required indexes against the current ORM. Confirm `activity_id`,
+`variant_id`, and `difficulty_level` columns from revision 0005. Revision 0004 describes
+historically pre-existing tables: blindly replaying migrations or stamping revision
+numbers is unsafe. Existing unrelated Quiz migration gaps are not solved by this work.
+Do not run `alembic upgrade`, seeds, `create_all`, `drop_all`, truncation or resets on
+the school database as part of a build, start, rollback or smoke test.
+
+Keep the already configured Railway → Supabase connection. Do not switch direct versus
+pooler mode, rotate credentials, change SSL options or guess a new hostname as part
+of this frontend correction. If the database owner identifies a connection problem,
+review it separately: psycopg prepared statements need configuration for transaction
+pooling, and transaction-mode port 6543 is not verified here. TLS and database
+reachability checks require permission to connect. Prefer a
+DB-owner-provisioned role limited to necessary Game tables/operations; none is created
+here. SQLAlchemy privileges, rather than browser-side RLS alone, protect this server
+connection. Default pool limits are 5 persistent plus 10 overflow connections per
+process; actual Railway worker/instance settings were not inspected. Confirm capacity
+before any separately approved scaling change.
+
+Keep three destinations separate: genuine school collection, development data, and
+synthetic browser/PostgreSQL tests. Use separate databases/projects, credentials,
+backend instances and browser profiles/origins. Do not rely on `STU_TEST` naming alone:
+the browser simulator intentionally uses `STU_001`/`STU_002`, which can overlap real codes.
+Never remove synthetic-looking rows from a shared database automatically. Preserve
+existing records and use the existing researcher verification/exclusion process.
+
+The browser simulator now checks `/health` before gameplay: it requires explicit
+synthetic opt-in and a SQLite/local PostgreSQL database with `test` or `synthetic` in
+its name. A loopback API connected to remote Supabase fails this check. PostgreSQL
+integration tests also reject non-loopback database hosts. Do not use a DB tunnel or
+proxy to make a remote school DB appear local. These guards prevent configuration
+mistakes; they do not establish the provenance of historical records.
+
+## Existing Railway service — only necessary proposed changes
+
+No Railway account/service/environment change is needed or authorized now. There is
+no new Railway deployment manifest: adding one could override the working shared
+service's builder or start command. Do not create another backend or deploy elsewhere.
+
+| Item | Proposed action, requiring review/approval before application |
+| --- | --- |
+| Shared entry point | Retain `app.main:app`; do not replace it with a Game-only app |
+| Start command/port | Keep the working command if it serves `app.main:app`, binds `0.0.0.0`, and consumes the platform `PORT`; no command change is established as necessary |
+| CORS | Once the Vercel domain exists, inspect current approved origins. If absent, add that exact origin through the prepared optional `CORS_ORIGINS` support, preserving `FRONTEND_URL` |
+| Game access block | A separately approved update to the existing Railway service must include the direct Game gate; local source does not change the running API |
+| Authorization | Review/approve and implement staff authentication, session grants, exports and cross-module access controls before release |
+| Database/runtime | Keep existing Supabase settings, schema, data, builder, dependencies and runtime; review actual compatibility separately |
+| Health | `/api/v1/health` is liveness only. Existing `/api/v1/db-health` remains a shared diagnostic route and was not called |
+
+If a future review finds the start command incompatible, this is a compatible
+reference from root `backend` (not a command to apply now):
+
+```sh
+uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-access-log
+```
+
+Do not add `--reload`, migrations, resets or seeds. Keep the service's working worker
+count unless separately reviewed. No `PYTHON_VERSION` change is prescribed; the repo's
+Python pin is 3.13.14, but the current Railway builder/runtime was not inspected.
+`CORS_ORIGINS` only takes effect after this prepared code is reviewed and deployed
+with approval; the old deployed revision may only understand `FRONTEND_URL`.
+
+Railway references: [system variables](https://docs.railway.com/variables/reference),
+[public networking and port binding](https://docs.railway.com/networking/public-networking).
+
+## Vercel steps — execute only after explicit deployment approval
+
+1. Create/import a separate project from the owner-approved remote revision. Set Root
+   Directory to `frontend`, framework to Vite, Node major to `24.x` (repository `.nvmrc`
+   is `24.18.0`), install command `npm ci`, build command `npm run build`, output `dist`.
+2. Set Production `VITE_API_BASE_URL=https://backend-production-b489d.up.railway.app/api/v1`
+   and `VITE_GAME_COLLECTION_ONLY=true`. These exact public settings are also documented
+   in `frontend/.env.example`. Do not add database credentials or export keys. Do not
+   copy this live URL into local gameplay tests; those require isolated loopback APIs.
+3. Keep Preview environment values separate. Use only an isolated test backend there;
+   never give previews a school API URL. Disable unintended automatic production
+   publishing in the project's Git/deployment settings before classroom collection.
+4. Keep `frontend/vercel.json`: the SPA fallback supports refresh/deep-link delivery;
+   existing asset requests still use their static files. No API proxy is configured.
+5. Deploy only after approval. The Vercel production domain is not known yet; obtain
+   it before proposing a final Railway CORS value. Do not allow `*.vercel.app` or all
+   previews. Changing domains/origins requires a pending-evidence plan.
+6. With this prepared build, verify the unavailable screen and absence of Game requests.
+   Teacher collection remains blocked. After approved authorization and restricted
+   workflow verification, test both modes, assets and fonts from a school computer.
+   Verify direct Railway access denials separately from page access.
+
+Provider reference: [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite).
+No hosted account settings were inspected or changed during preparation. The public
+Railway health URL could not be verified from this environment; that is a verification
+limit, not a finding that the existing service is down.
+
+## Production smoke checklist
+
+First run synthetic gameplay only against a separate staging database/backend using
+the approved authentication implementation. Never point the browser simulator at the
+live school database. A production write smoke check requires separate permission and
+an approved evidence classification; use only consenting real observations or an
+owner-approved designated test destination. Never insert fake student observations
+into the school collection to obtain a green check.
+
+- [ ] The blocked production frontend has no learner controls/canvas or Game requests,
+      including stored-evidence recovery. The prepared direct Railway Game gate returns
+      503; do not assume the current hosted revision already contains it.
+- [ ] Public liveness succeeds; the shared backend still mounts Game, Quiz and Tutor.
+      Existing docs/diagnostics are not removed by this correction. Review their access
+      alongside shared routes that can expose or create Game data before release.
+- [ ] Teacher can start a code-scoped collection without a student account; after
+      handoff the browser cannot switch codes or regain staff/export privileges without
+      fresh teacher authentication. Concurrent devices keep separate active grants.
+- [ ] Missing/invalid/expired credentials cannot read/write Game data through the direct API.
+- [ ] Learner A cannot query B's variant usage/result, append B's events/attempts,
+      complete B's session, or replay B's session creation even knowing its IDs/code.
+- [ ] Learners cannot export; only an authorized researcher can download the archive.
+- [ ] Exact allowed-origin CORS works; localhost/unapproved preview origins fail preflight.
+- [ ] Frontend has no requests to localhost, private keys, DB passwords, or source maps
+      containing private configuration. Browser communicates only with the approved API.
+- [ ] Two school devices using separately assigned codes get distinct session UUIDs and
+      save concurrently; DB owner reconciles source sessions/events/attempts/results.
+- [ ] For each mode, complete the unchanged six-task flow. Require **Saved** and
+      **Assessment complete**; verify acknowledged evidence in the authorized DB.
+- [ ] On staging, disconnect networking; verify Failed/Pending and blocked learner
+      switching. Restore networking and retry without changing payloads/IDs.
+- [ ] On staging, refresh and close/reopen the tab in the same origin/profile; reauthorize
+      the teacher's grant for the original learner and recover eligible evidence. Response-loss retries produce
+      no duplicate source evidence. Interrupted play remains incomplete.
+- [ ] Reload a deep URL and request known static assets. Check current Chrome/Edge,
+      Web Locks, storage availability, classroom bandwidth and service startup time.
+- [ ] Record approved revision, domains, database/project identity, operator, UTC time,
+      observed session IDs and verification outcome in a restricted release record.
+
+## Multiple-device and browser-storage limits
+
+The teacher must select and visually confirm the roster-assigned code on each device;
+the current code format check cannot detect a typo that is another valid assigned code.
+Keep the complete code-to-name roster separately, under approved access control.
+Do not collect the same learner concurrently on two devices: UUIDs remain unique, but
+variant history selection is not a reservation and can choose repeated variants.
+
+Each browser origin/profile has its own queue and a Web Lock preventing two collection
+tabs from writing it at once. Independent devices can submit separate sessions; the
+backend uses parent-row locks on PostgreSQL for retries of one session. SQLite tests
+cannot establish PostgreSQL concurrency or hosted capacity. Pending writes are stored
+before sending, retained until acknowledgement, and bound to their original student,
+session and backend destination. Learner switching is blocked until Saved and explicitly
+ended. Same-origin/Profile reopening preserves eligible evidence; unfinished gameplay
+state itself does not resume. Changing domain, scheme, port, browser or profile does
+not transfer the queue. HTTPS storage is independent from localhost storage.
+
+Browser localStorage is not encrypted research storage. Saved session metadata remains
+visible in that device/profile; closing the collection is not a secure data wipe.
+Approved managed-device/browser-profile policy is a release prerequisite. Separate
+learner profiles reduce access to prior local metadata; preserve any pending profile
+for recovery before cleanup under the approved retention policy. Do not silently clear
+storage or promise crash/power-loss/eviction recovery. Storage is bounded at 100 sessions,
+20,000 queued writes and 4 MiB; no evidence is evicted to make room.
+
+## Failure handling and rollback
+
+Stop new collection when recording/authentication fails. Preserve origin, browser
+profile, original API destination and pending IDs. Do not clear storage, switch DBs,
+retry into staging, manually manufacture completion, or delete production records.
+For CORS errors check the exact approved origin; for 503 in this prepared build resolve
+the authorization blocker. For a schema mismatch stop and obtain DBA review; do not
+apply migrations as an emergency workaround. Saved does not imply assessment complete.
+
+For transient network/service failure, reconnect and use **Retry / recover saved
+evidence**. Restore the approved login when access expires; ownership checks must
+still allow only the original learner's pending evidence. Preserve partial sessions
+as incomplete. Contact the researcher for full/unavailable storage or destination
+mismatch; do not keep playing and assume the latest action is durable.
+
+After explicit approval for a hosted rollback, restore the previous reviewed frontend
+version and backend code on the same domains/API/database. Check queue format, payload
+compatibility, authorization and retry behavior before releasing it. Do not roll back
+to the anonymous development entry. Keep automatic deployments off, do not downgrade
+or reset the database, and reconcile any in-flight/pending evidence after service
+restoration. If no safe compatible version exists, leave collection closed.
+
+## Verification record
+
+See `GAME_DEPLOYMENT_VERIFICATION.md` for local results and their limits. Successful
+local checks do not establish consent, production schema compatibility, live Supabase
+connectivity, or hosted browser recording. Approval of authentication, deployment,
+database access and the smoke checklist is still required before teacher handoff.

diff --git a/docs/GAME_DEPLOYMENT_VERIFICATION.md b/docs/GAME_DEPLOYMENT_VERIFICATION.md
new file mode 100644
--- /dev/null
+++ b/docs/GAME_DEPLOYMENT_VERIFICATION.md
@@ -0,0 +1,144 @@
+# Local deployment-preparation verification — October 16, 2026
+
+**Existing Railway backend: owner confirmed. Vercel collection frontend: NOT DEPLOYED.**
+**Vercel → Railway → Supabase saving: NOT VERIFIED. Production collection: BLOCKED.**
+
+No direct remote database connection or collection/data-endpoint calls were made.
+A read-only public liveness request could not be completed from this environment;
+this does not establish a Railway outage. No migrations, hosting operations, commits, pushes,
+merges or branch switches occurred. Existing uncommitted research/visual changes were
+preserved. Local synthetic SQLite files and browser evidence are retained separately
+under ignored `tmp/` and `frontend/artifacts/`, not treated as learner observations.
+
+## Results
+
+| Check | Result |
+| --- | --- |
+| Game-only frontend production build | Passed with the owner-supplied `VITE_API_BASE_URL=https://backend-production-b489d.up.railway.app/api/v1` and `VITE_GAME_COLLECTION_ONLY=true`; production Game gate stays closed |
+| Normal team frontend production build | Passed for the Railway correction with the same public API URL and `VITE_GAME_COLLECTION_ONLY=false`; Quiz/Tutor/Avatar modules still build |
+| Frontend unit/regression tests | 16 passed, including durable Game retry, reopen, destination mismatch, blocked switching and independent device queues |
+| Backend Game/deployment/recording/export/ML/research regression set | Railway correction: 278 passed, 2 skipped |
+| Opt-in PostgreSQL checks | Skipped: Game content migration and Game PostgreSQL collection; no disposable PostgreSQL URL configured |
+| Production perimeter | Passed: every Game endpoint fails closed before DB access, including known-code/session reads and supplied bearer credentials |
+| Shared Railway health/CORS/surface | Passed: database-free liveness; Game/Quiz/Tutor route paths preserved; existing HTTPS frontend origin plus additional Vercel origin allowed; hosted localhost regex disabled; hosted synthetic-test opt-in refused |
+| Hosted detection | Passed: Railway injected IDs require no added variable; `GAME_DEPLOYMENT_ENV=development` cannot bypass Railway detection; `app.main:app` remains the entry |
+| Negative build configuration | Passed: missing backend URL, localhost URL and `VITE_DATABASE_PASSWORD` rejected |
+| Game production asset scan | Passed: exact owner-supplied Railway API base and unavailable gate present; no default localhost API, PostgreSQL URLs or known private-key setting names in emitted JavaScript; no hosted network verification implied |
+| Vercel/provider configuration | `frontend/vercel.json` retains Vite, `npm ci`, `npm run build`, `dist` and SPA fallback; no replacement backend manifest. Railway dashboard/env/builder/start command were not inspected or changed |
+| Changed Python files | Ruff passed |
+| Git diff review | Deployment changes reviewed; `git diff --check` passed; existing unrelated changes remain present |
+| CSV browser download | Passed on new Game-only entry against empty local SQLite, including invalid-key denial and actual archive download; passed again after making the test select its own entry flag |
+| Reusable access-control inspection | Only Game/Quiz static export-key dependencies found; no staff login, provider JWT verification or session ownership store. Staff-only access proposal documented; no authentication implementation or provider change performed |
+| Full Game recording browser regression | Earlier local-development run passed both modes into fresh SQLite: wrong/correct answers, hints, response-loss replay, refresh/tab-close recovery and learner switching. Not a production saving test; not rerun for this correction |
+| Production frontend browser block | Passed `gameProductionGate.e2e.mjs`: built Game entry has no learner controls/canvas/export UI, no API requests, and no pending-storage recovery/clearing. Test intercepts and aborts API requests before networking as an extra safeguard |
+| Tutor regression checks | 76 passed in a separate SQLite-only pytest process |
+| Quiz regression checks | 21 passed, 1 failed: `test_quiz_seed.py:117` expects `is_correct` absent from an answer response. Reproduced with the original committed `app.main` loaded in memory, without replacing source; not introduced by the Railway correction. Quiz business logic left unchanged |
+| Browser evidence → SQLite → CSV reconciliation | Passed with a read-only SQLite connection: six unique learner-bound sessions, four completed results, two incomplete sessions, 37 matching browser answers, unique retry event keys and matching source event IDs in CSV |
+| Existing Game language browser regression | Failed `summaryBounds.siBottom <= summaryBounds.enTop` at `gameLanguage.e2e.mjs:248`; summary language-layout issue remains unresolved; visual source was not changed by this preparation |
+
+Production builds emit the existing large-bundle warning (Phaser); this is not a
+build failure. Backend tests emit a Starlette/httpx deprecation warning. Local tools
+were Python 3.13.12 and Node 22.19.0. Vercel configuration targets Node 24.x;
+the repo Python pin is 3.13.14, but no change to Railway's existing runtime is
+prescribed or applied. Provider installation/runtime settings remain unverified.
+
+The first backend run could not use Windows' default pytest temporary directory:
+230 cases passed but 44 fixture setups raised permission errors. The corrected run
+used a newly allocated workspace-local `--basetemp`, disabled the unwritable pytest
+cache, and passed the complete selected set. No application change was made for this
+environment issue. Initial sandbox browser attempts lost Chrome/Edge debugging
+connections; browser checks required running outside that sandbox. The first
+unsandboxed CSV attempt used the normal Tutor-default entry; rerunning with the
+intended Game-only flag passed.
+
+The first full recording attempt completed Drag & Drop checks and one Hangman
+assessment, then timed out while loading a replacement tab. The isolated rerun
+passed after allowing up to 60 seconds for the initial collection form to load.
+Recording and CSV browser tests now explicitly select the Game-only entry instead
+of relying on the normal application's default module. Full recording evidence:
+`frontend/artifacts/game-collection-1792151460014/browser-evidence.json`.
+CSV download evidence: `frontend/artifacts/csv-download-1792151073816/`.
+Final self-configuring CSV browser run: `frontend/artifacts/csv-download-1792151967851/`.
+The disposable SQLite target used a workspace-only helper at
+`tmp/deployment_synthetic_api.py`; it never inherits the application's database URL.
+The language-layout failure must be assessed before classroom handoff; this report
+does not claim every browser test passes.
+Read-only reconciliation exports are retained at
+`tmp/deployment-synthetic-export-ee16ab3f5b954fd9898d44459628e0ed/`.
+
+## Files in this preparation
+
+| Area | Added | Modified |
+| --- | --- | --- |
+| Hosting | `frontend/vercel.json`, `frontend/.env.example` | `.env.example`, `frontend/vite.config.ts` |
+| Backend | `backend/app/core/game_deployment.py`, `backend/app/core/collection_safety.py`, `backend/tests/test_game_deployment.py` | `backend/app/main.py`, `backend/app/core/config.py` |
+| Frontend | `frontend/src/game/GameCollectionApp.tsx`, `frontend/src/game/CollectionUnavailable.tsx`, `frontend/tests/gameCollectionRecovery.test.ts`, `frontend/tests/gameProductionGate.e2e.mjs` | `frontend/src/main.tsx`, `frontend/src/game/CollectionGate.tsx`, `frontend/src/game/api/collectionStore.ts`, `frontend/tests/gameCollection.e2e.mjs`, `frontend/tests/gameCsvDownload.e2e.mjs` |
+| Guides | `docs/GAME_DEPLOYMENT.md`, `docs/GAME_TEACHER_GUIDE.md`, `docs/GAME_ACCESS_CONTROL_PROPOSAL.md`, this verification record | None |
+
+Pre-existing changes in ML milestones, research schemas and Game visuals/browser-UI
+tests are outside this inventory and remain intact. The ignored synthetic helper,
+databases and evidence directories are local verification artifacts, not hosting inputs.
+Superseded preparation artifacts `render.yaml` and `backend/app/collection_main.py`
+were removed locally; they were never deployed or used to create hosting resources.
+
+## Reproduce backend checks safely (PowerShell, from backend)
+
+Use installed development/ML test dependencies. Always override the application's
+database setting and clear opt-in test URLs when no isolated local PostgreSQL exists.
+The unique scratch path below must not be an existing evidence directory: pytest
+owns and cleans its base temporary directory.
+
+```powershell
+$env:DATABASE_URL = 'sqlite+pysqlite:///:memory:'
+$env:GAME_DEPLOYMENT_ENV = 'development'
+$env:RAILWAY_ENVIRONMENT_ID = ''
+$env:RAILWAY_SERVICE_ID = ''
+$env:GAME_COLLECTION_TEST_DATABASE_URL = ''
+$env:GAME_CONTENT_TEST_DATABASE_URL = ''
+$env:GAME_CONTENT_MIGRATION_TEST_DATABASE_URL = ''
+$testScratch = Join-Path (Resolve-Path ../tmp) ('deployment-pytest-' + [guid]::NewGuid().ToString('N'))
+.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp $testScratch --tb=short tests/test_game_deployment.py tests/test_game_sessions_api.py tests/test_game_collection_download.py tests/test_game_export_cli.py tests/test_game_activity_bank.py tests/test_game_ml.py tests/test_game_research_ml.py tests/test_game_collection_research.py tests/test_game_session_verification.py tests/test_game_postgres_collection.py
+```
+
+## Reproduce frontend checks safely (PowerShell, from frontend)
+
+```powershell
+$env:VITE_API_BASE_URL = 'https://backend-production-b489d.up.railway.app/api/v1'
+$env:VITE_GAME_COLLECTION_ONLY = 'true'
+npm.cmd run build
+npm.cmd test
+node tests/gameProductionGate.e2e.mjs
+$env:DATABASE_URL = 'sqlite+pysqlite:///:memory:'
+$env:GAME_DEPLOYMENT_ENV = 'development'
+node tests/gameCsvDownload.e2e.mjs
+```
+
+For `gameCollection.e2e.mjs`, use a separately started fresh local synthetic server.
+Set `GAME_SYNTHETIC_COLLECTION=true` on that server, with an explicitly isolated
+local database named with `test` or `synthetic`, and
+`GAME_COLLECTION_API=http://127.0.0.1:8137/api/v1` on the browser process. The recording
+and CSV tests select `VITE_GAME_COLLECTION_ONLY=true` themselves. The handshake
+rejects remote databases even if the API itself listens on loopback. The local
+recording run here uses disposable SQLite, which cannot verify PostgreSQL row locks,
+Supabase schema, TLS, network reachability, live concurrency or classroom load.
+
+The production block browser test uses local static preview and intercepts/aborts
+all API requests before they reach Railway. The CSV test starts its own empty SQLite
+API and loopback Vite development server, overriding the public frontend URL.
+Never run development gameplay with the live Railway API URL.
+
+The existing language test expects normal application navigation; run it with
+`VITE_GAME_COLLECTION_ONLY=false`. It uses synthetic response fixtures and no database,
+so it is not evidence of backend recording.
+
+## Before teacher handoff
+
+Review [GAME_ACCESS_CONTROL_PROPOSAL.md](GAME_ACCESS_CONTROL_PROPOSAL.md): repository
+inspection found only narrow static export keys and no reusable staff login. The
+recommended staff-only managed identity and locked teacher collection grants remain
+unimplemented. Confirm approved authentication and consent/data handling, implement
+and test session authorization and researcher roles, confirm actual Game schema and network compatibility
+with the DB owner, select the Vercel domain, obtain explicit environment/deployment/
+database-access approval, update only the existing Railway service when approved,
+and complete the production checklist in
+[GAME_DEPLOYMENT.md](GAME_DEPLOYMENT.md). Until then there is no verified teacher URL.

diff --git a/docs/GAME_TEACHER_GUIDE.md b/docs/GAME_TEACHER_GUIDE.md
new file mode 100644
--- /dev/null
+++ b/docs/GAME_TEACHER_GUIDE.md
@@ -0,0 +1,41 @@
+# Teacher guide — Game collection website
+
+**The Vercel collection website is not deployed yet. The existing backend is on Railway.**
+**Do not collect through this preparation build: production Game access is blocked.**
+Use these instructions only after the researcher supplies an approved, verified
+HTTPS link and the approved sign-in/access instructions.
+
+1. Use a school computer with current Chrome or Edge, normal browsing and the assigned
+   managed browser profile. Open the researcher's exact link. The authorized teacher
+   signs in as instructed; the student does not need an account. Before handoff,
+   confirm the approved system has locked this device to the learner's collection.
+   No localhost, software installation or development server is needed on school devices.
+2. Check consent and the learner's assigned code using the private approved roster.
+   Enter only the code, such as `STU_001`, and click **Set student**. Check the visible
+   active code before the learner starts. Codes are identifiers; they are not passwords.
+   Keep the roster and researcher download credentials away from student screens.
+3. Choose **Drag & Drop** or **Hangman**. The application creates a new session for
+   each game. Let the learner play using the existing instructions and language toggle.
+4. Watch **Saved / Pending / Failed**. **Saved** means the current evidence was
+   acknowledged. A finished assessment also needs **Assessment complete** and its
+   backend result summary. Do not record an interrupted game as complete.
+5. Before the other game or a different learner, check the ending confirmation and
+   click **End collection / switch learner**. Follow the approved teacher
+   reauthentication step, then enter and confirm the assigned code again.
+   Do not move the same learner between computers during an open session.
+6. If networking fails, stop new play, restore the connection and click **Retry /
+   recover saved evidence**. Pending/failed evidence must be recovered before switching.
+   If sign-in expired, follow the approved sign-in recovery instructions.
+7. After accidental refresh/tab closure, reopen the exact same link in the same browser
+   profile. Enter the original learner's code and recover the evidence. An unfinished
+   game cannot resume its previous screen: end its recovered collection, then start a
+   new session if the researcher permits it. The earlier session stays incomplete.
+8. For a persistent failure, full storage, access denial or a destination warning, stop
+   and contact the researcher. Keep the profile and note the displayed code/session ID
+   through the approved private channel. Do not clear browser data, use private mode,
+   change domains/profiles or attempt another backend link.
+
+Use one Game collection tab per browser profile. Follow the researcher's managed-device
+and retention instructions between learners; local session metadata can remain on the
+computer after **End collection**. The researcher handles downloads and database checks
+on an approved researcher device. Do not enter their export key on a student computer.

````

## Withdrawn local synthetic API helper

````python
"""Disposable SQLite HTTP target for this deployment-preparation browser run."""
import os
import sys
import uuid
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
database = root / "tmp" / f"deployment-synthetic-{uuid.uuid4().hex}.sqlite"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///" + database.as_posix()
os.environ["GAME_DEPLOYMENT_ENV"] = "development"
os.environ["GAME_SYNTHETIC_COLLECTION"] = "true"

import uvicorn
from app.main import app
from app.db.base import Base
from app.db.session import engine
from app.modules.game.models import GameSession, GameplayEvent, GameTaskAttempt, GameResult

assert engine.url.get_backend_name() == "sqlite"
Base.metadata.create_all(engine, tables=[GameSession.__table__, GameplayEvent.__table__, GameTaskAttempt.__table__, GameResult.__table__])
print("Synthetic local evidence database:", database, flush=True)
uvicorn.run(app, host="127.0.0.1", port=8137, access_log=False)

````

## Completed source rollback verification

Restored all nine deployment-modified tracked files to their pre-preparation Git
version. Removed all thirteen deployment-added source/config/test/guide files after
archiving them above. Removed the ignored synthetic server helper after archiving it.
All 23 unrelated changed/untracked files are byte-for-byte unchanged, verified by
SHA-256 before and after rollback. The Git index remains empty, and the branch and
base commit are unchanged. Only this new review document remains from deployment
preparation in the active working-tree diff. Local ignored synthetic evidence remains
preserved. No commit, push, merge, branch switch, hosting action or database operation
was performed.

## Post-rollback checks

- Frontend `npm run build`: passed for the restored normal application, with an
  explicit loopback API URL in this build process only. No real environment file
  was changed. The ignored `frontend/dist` output was rebuilt so it no longer
  contains the withdrawn production unavailable gate. The existing large-bundle
  warning remains.
- Frontend `npm test`: 14 existing tests passed. The two deployment-added queue
  tests were removed with the deployment preparation and remain archived above.
- Backend Game sessions API, researcher download and export CLI checks: 41 passed
  in the initial local-SQLite run. Two export cases failed when the generated
  Windows output filename reached 260 characters; both passed on rerun using a
  shorter fresh workspace-local temporary path. No source fix was needed. All
  43 selected cases therefore passed across those runs.
- Final working-tree verification: the original 23 changed/untracked files plus
  this one Markdown archive only. All nine reverted files match their base Git
  contents, and every preserved source file matches its pre-rollback SHA-256.
- Git diff whitespace check: passed. The existing CRLF normalization notice for
  the preserved research dataset schema remains unrelated to this rollback.
- No commit, push, merge, branch switch, hosting/environment change, production
  database access or schema/data operation was performed.

The deployment work is deferred pending the owner's team discussion. The restored
baseline and preserved unrelated changes are not a guarantee of a conflict-free
merge with branches that have not been compared.
