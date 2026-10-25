"""This subrouter grants no public/session-ID-only inference access."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from .access import ResearchAccess, require_research_access, unavailable
from .service import PredictionResponse, predict_saved_session

router = APIRouter()


def research_database(
    access: Annotated[ResearchAccess, Depends(require_research_access)],
    database: Annotated[Session, Depends(get_db)],
):
    # Authorization/manifest dependencies resolve before database dependency.
    if database.new or database.dirty or database.deleted:
        raise unavailable()
    try:
        with database.no_autoflush:
            dialect = database.get_bind().dialect.name
            if dialect == "postgresql":
                if database.in_transaction():
                    raise unavailable()
                database.connection().exec_driver_sql(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                )
            elif dialect != "sqlite":
                raise unavailable()
            yield database
    except SQLAlchemyError:
        raise unavailable() from None
    finally:
        database.rollback()


@router.get("/sessions/{game_session_id}/ml-prediction", response_model=PredictionResponse)
def research_prediction(
    response: Response,
    access: Annotated[ResearchAccess, Depends(require_research_access)],
    database: Annotated[Session, Depends(research_database)],
) -> PredictionResponse:
    response.headers["Cache-Control"] = "no-store"
    return predict_saved_session(access, database)
