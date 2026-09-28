"""Small Calendar composition root borrowing shared DB, Redis and lock resources."""

import httpx

from app.core.config import Settings
from app.database.session import DatabaseManager
from app.modules.calendar.actions import CalendarActions
from app.modules.calendar.audit import CalendarAudit
from app.modules.calendar.auth import GoogleTokenProvider
from app.modules.calendar.client import GoogleCalendarClient
from app.modules.calendar.credentials import GoogleCredentialStore
from app.modules.calendar.exceptions import CalendarConfigurationError
from app.modules.calendar.oauth import GoogleOAuthService
from app.modules.calendar.service import CalendarService
from app.modules.calendar.state import MemoryTemporaryStore, RedisTemporaryStore, TemporaryStore
from app.modules.security.lock_service import LockService
from app.redis.manager import RedisManager


class CalendarRuntime:
    def __init__(
        self,
        settings: Settings,
        database: DatabaseManager | None,
        redis: RedisManager | None,
        lock: LockService,
    ) -> None:
        self.settings = settings
        self.store = GoogleCredentialStore(
            database, settings.telegram_owner_id, settings.data_encryption_key
        )
        self.states: TemporaryStore = MemoryTemporaryStore()
        if settings.oauth_state_backend == "redis":
            if redis is None:
                raise CalendarConfigurationError("OAUTH_STATE_BACKEND=redis requires REDIS_URL.")
            self.states = RedisTemporaryStore(
                redis.client, settings.redis_key_prefix, settings.telegram_owner_id or 0
            )
        self.http = httpx.AsyncClient(timeout=20, follow_redirects=False)
        audit = CalendarAudit(database, settings.telegram_owner_id)
        self.tokens = GoogleTokenProvider(settings, self.store)
        self.service = CalendarService(
            GoogleCalendarClient(self.http, self.tokens, settings.google_calendar_id),
            audit,
            settings.timezone,
        )
        self.oauth = GoogleOAuthService(settings, self.store, self.states, lock, audit, self.http)
        self.actions = CalendarActions(
            self.service, self.oauth, self.states, settings.telegram_owner_id
        )

    async def close(self) -> None:
        await self.http.aclose()
