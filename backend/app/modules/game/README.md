# Game module (backend)

**Owner:** RehanOP007 (Game component). Other components: please don't edit
files here. Open an issue or ask the owner instead.

Backend for the Equation Game. Its routes are served under `/api/v1/game`.

| File | Purpose |
| --- | --- |
| `router.py` | FastAPI routes, mounted in `app/main.py` |
| `schemas.py` | Pydantic request/response models |
| `service.py` | Game logic: sessions, scoring, building results |
| `models.py` | SQLAlchemy tables (`game_results`) |

Tests go in `backend/tests/test_game_*.py`.

## Shared contract with the AI Tutor

The AI Tutor reads `GameResult` from `models.py` (`tutor/service.py`), and its
input contract is `GameResult` in `app/modules/tutor/schemas.py`. Renaming or
removing a column or allowed value breaks the Tutor, so agree such changes with
the Tutor owner first. Adding new nullable columns is safe.

Any schema change needs an Alembic migration:

```sh
cd backend
alembic revision --autogenerate -m "game: <change>"
```

Coordinate with the team before running `alembic upgrade` against the shared
Supabase database.
