"""Audit only purpose-built metadata, never raw messages or credential payloads."""

import json
from ipaddress import ip_address as parse_ip

from app.core.exceptions import AuditDetailsError
from app.database.models import AuditLog
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository

SENSITIVE_PARTS = (
    "password",
    "secret",
    "token",
    "pin",
    "apikey",
    "apihash",
    "sessionstring",
    "authorization",
    "cookie",
    "databaseurl",
    "redisurl",
    "encryptionkey",
)


def validated_details(details: dict[str, object] | None) -> dict[str, object]:
    """Reject known credential keys and non-JSON values; this is not a secret detector."""

    def inspect(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise AuditDetailsError("Audit detail keys must be strings.")
                normalized = "".join(c for c in key.lower() if c.isalnum())
                if any(part in normalized for part in SENSITIVE_PARTS):
                    raise AuditDetailsError("Sensitive audit detail fields are prohibited.")
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
        elif value is not None and not isinstance(value, (str, bool, int, float)):
            raise AuditDetailsError("Audit details must contain JSON values only.")

    if details is not None and not isinstance(details, dict):
        raise AuditDetailsError("Audit details must be a JSON object.")
    try:
        inspect(details)
        encoded = json.dumps(details if details is not None else {}, allow_nan=False)
        if len(encoded.encode("utf-8")) > 16384:
            raise AuditDetailsError("Audit details exceed 16 KiB.")
        return json.loads(encoded)
    except (TypeError, ValueError, RecursionError):
        raise AuditDetailsError(
            "Audit details must be bounded JSON without sensitive fields."
        ) from None


class AuditService:
    """Append audit events in the caller's transaction; never commit or log payloads."""

    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    async def log_event(
        self,
        action: AuditAction,
        *,
        user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        details: dict[str, object] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        if not isinstance(action, AuditAction):
            raise TypeError("Unsupported audit action")
        if ip_address is not None:
            try:
                ip_address = str(parse_ip(ip_address))
            except ValueError:
                raise ValueError("Invalid audit IP address") from None
        return await self.repository.add(
            AuditLog(
                action=action.value,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                details=validated_details(details),
                ip_address=ip_address,
            )
        )
