import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import application_context
from app.api.schemas.health import HealthResponse, LivenessResponse, ReadinessResponse, Services
from app.core.application import ApplicationContext
from app.database.health import check_database_health
from app.redis.health import check_redis_health

router = APIRouter(prefix="/health")
type Context = Annotated[ApplicationContext, Depends(application_context)]


async def snapshot(context: ApplicationContext) -> HealthResponse:
    async def database() -> str:
        if context.database is None:
            return "not_configured"
        return "ok" if await check_database_health(context.database.engine) else "unavailable"

    async def redis() -> str:
        if context.redis is None:
            return "not_configured"
        return "ok" if await check_redis_health(context.redis.client) else "unavailable"

    db, cache = await asyncio.gather(database(), redis())
    notebook_storage = context.runtime.notebook_storage
    if context.notebook is not None:
        notebook_storage = (
            "available" if await context.notebook.storage.health() else "unavailable"
        )
    services = Services(
        application="ok" if context.runtime.startup_complete else "unavailable",
        database=db,
        redis=cache,
        telegram=context.runtime.telegram,
        reminder_scheduler=context.runtime.reminder_scheduler,
        gmail=context.runtime.gmail,
        personal_telegram=context.runtime.personal_telegram,
        notebook_storage=notebook_storage,
        daily_automation=context.runtime.daily_automation,
    )
    required_failed = (
        not context.runtime.startup_complete
        or (context.settings.security_state_backend == "redis" and cache != "ok")
        or (context.runtime.telegram_required and context.runtime.telegram != "running")
        or (
            context.runtime.reminder_scheduler_required
            and context.runtime.reminder_scheduler != "running"
        )
    )
    status = (
        "error"
        if required_failed
        else (
            "ok"
            if db == cache == "ok"
            and services.telegram in {"configured", "running"}
            and services.reminder_scheduler in {"disabled", "running"}
            and services.gmail in {"disabled", "not_configured", "connected", "monitoring"}
            and services.personal_telegram
            in {"disabled", "not_configured", "connected", "monitoring"}
            and services.notebook_storage in {"not_configured", "available"}
            and services.daily_automation in {"disabled", "running"}
            else "degraded"
        )
    )
    return HealthResponse(status=status, services=services)


@router.get("", response_model=HealthResponse)
async def health(response: Response, context: Context) -> HealthResponse:
    result = await snapshot(context)
    response.status_code = 503 if result.status == "error" else 200
    return result


@router.get("/live", response_model=LivenessResponse)
async def live() -> LivenessResponse:
    return LivenessResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def ready(response: Response, context: Context) -> ReadinessResponse:
    result = await snapshot(context)
    response.status_code = 503 if result.status == "error" else 200
    return ReadinessResponse(status="not_ready" if result.status == "error" else "ready")
