from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.dependencies.database import get_database_session
from app.schemas.health import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> HealthCheckResponse | JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except (OSError, SQLAlchemyError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthCheckResponse(
                status="error",
                service=settings.app_name,
                environment=settings.app_env,
                database="unavailable",
            ).model_dump(),
        )

    return HealthCheckResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        database="ok",
    )
