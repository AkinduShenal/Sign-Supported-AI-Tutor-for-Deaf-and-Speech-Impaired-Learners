# Sign-Supported AI Tutor

Research project for accessible Grade 10 Mathematics learning support for Deaf
and speech-impaired learners.

## Project structure

- `backend/` — FastAPI API, tutor strategy logic, lesson content, sign planner,
  database models, migrations, and tests.
- `frontend/` — React/Vite lesson interface and the runtime avatar player.
- `frontend/public/models/louise_signs_master.glb` — deployed Louise avatar with
  named prototype gesture actions.
- `avatar-sign-package/` — canonical sign manifests, review documentation,
  technical pose report, and asset validation/build tools.
- `avatar/` — deprecated procedural research script retained for reference only;
  it is not used by the application.

`backend/app/modules/tutor/sign_package/` is a deployment snapshot of the two
canonical manifest files because Railway deploys the backend directory by
itself. A test prevents the snapshot and canonical files from drifting apart.

## Run locally

Backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`.

The main page contains the Grade 10 adaptive linear-equation workspace. Open
**Lesson setup / team diagnostic handoff** to preview four difficulty paths or
import Quiz/Game diagnostic JSON. See [the implementation and research guide](docs/GRADE10_TUTOR.md)
for API integration, tests, model status and remaining validation requirements.

## Avatar research status

The master GLB contains 56 technically checked prototype educational gesture
actions: 22 repaired core actions plus 34 review-only composites. They are not
validated Sri Lankan Sign Language. Missing or unavailable actions fall back to
written and visual mathematics support rather than being fabricated at runtime.

Validated-only playback is the default. To review existing unvalidated gestures,
explicitly enable **Preview unvalidated gestures (reviewers only)**. The current
strategy engine is a rule-based baseline, not a trained ML model. Teacher/sign
review and actual learner evaluation remain necessary before research claims.
