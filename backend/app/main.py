from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.modules.tutor.router import router as tutor_router


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tutor_router)

# Integrate Linear Equation AI Tutor service
try:
    from app.modules.non_improvement_section_tutor.main import router as linear_tutor_router
    from app.modules.non_improvement_section_tutor.services.db import init_db as init_linear_tutor_db
    app.include_router(linear_tutor_router)
except Exception as _tutor_import_err:
    init_linear_tutor_db = None
    print(f"[WARN] Could not import Linear Equation Tutor: {_tutor_import_err}")


@app.on_event("startup")
def startup_event():
    if init_linear_tutor_db:
        try:
            init_linear_tutor_db()
        except Exception as _db_err:
            print(f"[WARN] Linear Equation Tutor init_db error: {_db_err}")


@app.get("/api/v1/health", tags=["System"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "sign-supported-ai-tutor-api",
    }


@app.get("/api/v1/db-health", tags=["System"])
def database_health_check() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
