import httpx

from app.core.config import Settings
from app.database.session import DatabaseManager
from app.modules.calendar.credentials import GoogleCredentialStore
from app.modules.calendar.state import MemoryTemporaryStore, RedisTemporaryStore, TemporaryStore
from app.modules.email.audit import EmailAudit
from app.modules.email.client import GmailClient, GmailTokenProvider
from app.modules.email.delivery import TelegramEmailDelivery
from app.modules.email.drafts import ReplyDraftService
from app.modules.email.exceptions import GmailConfigurationError
from app.modules.email.monitor import GmailMonitor
from app.modules.email.oauth import GmailOAuthService
from app.modules.email.service import EmailService
from app.modules.email.summarizer import DeterministicEmailSummarizer
from app.modules.security.lock_service import LockService
from app.redis.manager import RedisManager


class EmailRuntime:
    def __init__(
        self,
        settings: Settings,
        database: DatabaseManager,
        redis: RedisManager | None,
        lock: LockService,
        bot=None,
    ) -> None:
        if settings.telegram_owner_id is None or settings.data_encryption_key is None:
            raise GmailConfigurationError("Gmail requires owner ID and DATA_ENCRYPTION_KEY.")
        self.settings = settings
        self.store = GoogleCredentialStore(
            database, settings.telegram_owner_id, settings.data_encryption_key, "google_gmail"
        )
        self.states: TemporaryStore = MemoryTemporaryStore()
        if settings.oauth_state_backend == "redis":
            if redis is None:
                raise GmailConfigurationError("OAUTH_STATE_BACKEND=redis requires Redis.")
            self.states = RedisTemporaryStore(
                redis.client, f"{settings.redis_key_prefix}:gmail", settings.telegram_owner_id
            )
        self.http = httpx.AsyncClient(timeout=20, follow_redirects=False)
        self.tokens = GmailTokenProvider(settings, self.store)
        self.audit = EmailAudit(database, settings.telegram_owner_id)
        notifier = TelegramEmailDelivery(bot, settings.telegram_owner_id) if bot else None
        client = GmailClient(self.http, self.tokens)
        self.service = EmailService(
            database,
            settings.telegram_owner_id,
            settings.data_encryption_key,
            client,
            DeterministicEmailSummarizer(),
            notifier,
            recent_limit=settings.gmail_recent_list_limit,
            notify_mode=settings.gmail_notify_mode,
        )
        self.oauth = GmailOAuthService(settings, self.store, self.states, lock, self.audit)
        self.drafts = ReplyDraftService(
            database, settings.telegram_owner_id, settings.data_encryption_key, client
        )
        self.monitor = GmailMonitor(
            self.service, settings.gmail_poll_interval_seconds, settings.gmail_initial_sync_limit
        )

    async def connected(self) -> bool:
        return await self.store.load() is not None

    async def close(self) -> None:
        await self.monitor.stop()
        await self.http.aclose()
