from typing import Literal

from pydantic import BaseModel

type ServiceStatus = Literal[
    "ok",
    "configured",
    "not_configured",
    "not_connected",
    "connected",
    "monitoring",
    "available",
    "unavailable",
    "error",
    "running",
    "stopped",
    "disabled",
]


class Services(BaseModel):
    application: ServiceStatus
    database: ServiceStatus
    redis: ServiceStatus
    telegram: ServiceStatus
    reminder_scheduler: ServiceStatus
    gmail: ServiceStatus
    personal_telegram: ServiceStatus
    notebook_storage: ServiceStatus
    daily_automation: ServiceStatus


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    services: Services


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]


class LivenessResponse(BaseModel):
    status: Literal["alive"] = "alive"
