from __future__ import annotations

from datetime import time
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load configuration without connections. Never log the full settings object.

    Feature startup must validate its required credentials before use.
    """

    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_timezone: str = Field(default="Asia/Tashkent", alias="APP_TIMEZONE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_host: str = Field(default="127.0.0.1", min_length=1, alias="API_HOST")
    api_port: int = Field(default=8000, ge=1, le=65535, alias="API_PORT")
    security_state_backend: Literal["memory", "redis"] = Field(
        default="memory", alias="SECURITY_STATE_BACKEND"
    )
    session_lock_enabled: bool = Field(default=True, alias="SESSION_LOCK_ENABLED")
    redis_key_prefix: str = Field(
        default="personal_ai", pattern=r"^[a-zA-Z0-9:_-]{1,64}$", alias="REDIS_KEY_PREFIX"
    )
    google_client_id: SecretStr | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: SecretStr | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str | None = Field(default=None, alias="GOOGLE_REDIRECT_URI")
    google_calendar_id: str = Field(default="primary", min_length=1, alias="GOOGLE_CALENDAR_ID")
    data_encryption_key: SecretStr | None = Field(default=None, alias="DATA_ENCRYPTION_KEY")
    oauth_state_backend: Literal["memory", "redis"] = Field(
        default="memory", alias="OAUTH_STATE_BACKEND"
    )
    calendar_default_event_duration_minutes: int = Field(
        default=60, ge=1, le=1440, alias="CALENDAR_DEFAULT_EVENT_DURATION_MINUTES"
    )
    run_reminder_scheduler: bool = Field(default=False, alias="RUN_REMINDER_SCHEDULER")
    run_daily_automation: bool = Field(default=False, alias="RUN_DAILY_AUTOMATION")
    daily_morning_default_time: str = Field(
        default="08:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$", alias="DAILY_MORNING_DEFAULT_TIME"
    )
    daily_evening_default_time: str = Field(
        default="20:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$", alias="DAILY_EVENING_DEFAULT_TIME"
    )
    daily_automation_grace_minutes: int = Field(
        default=120, ge=0, le=720, alias="DAILY_AUTOMATION_GRACE_MINUTES"
    )
    daily_delivery_max_attempts: int = Field(
        default=3, ge=1, le=5, alias="DAILY_DELIVERY_MAX_ATTEMPTS"
    )
    run_gmail_monitor: bool = Field(default=False, alias="RUN_GMAIL_MONITOR")
    gmail_poll_interval_seconds: int = Field(
        default=60, ge=30, le=3600, alias="GMAIL_POLL_INTERVAL_SECONDS"
    )
    gmail_initial_sync_limit: int = Field(default=30, ge=1, le=100, alias="GMAIL_INITIAL_SYNC_LIMIT")
    gmail_recent_list_limit: int = Field(default=10, ge=1, le=20, alias="GMAIL_RECENT_LIST_LIMIT")
    gmail_notify_mode: Literal["all", "important", "unread"] = Field(
        default="all", alias="GMAIL_NOTIFY_MODE"
    )
    personal_telegram_enabled: bool = Field(default=False, alias="PERSONAL_TELEGRAM_ENABLED")
    personal_telegram_session_backend: Literal["database"] = Field(
        default="database", alias="PERSONAL_TELEGRAM_SESSION_BACKEND"
    )
    run_personal_telegram_monitor: bool = Field(
        default=True, alias="RUN_PERSONAL_TELEGRAM_MONITOR"
    )
    personal_telegram_initial_sync_limit: int = Field(
        default=30, ge=1, le=100, alias="PERSONAL_TELEGRAM_INITIAL_SYNC_LIMIT"
    )
    personal_telegram_recent_limit: int = Field(
        default=10, ge=1, le=20, alias="PERSONAL_TELEGRAM_RECENT_LIMIT"
    )
    personal_telegram_monitor_scope: Literal["private", "all"] = Field(
        default="private", alias="PERSONAL_TELEGRAM_MONITOR_SCOPE"
    )
    finance_default_currency: Literal["UZS", "USD", "EUR"] = Field(
        default="UZS", alias="FINANCE_DEFAULT_CURRENCY"
    )
    finance_recent_limit: int = Field(default=10, ge=1, le=50, alias="FINANCE_RECENT_LIMIT")
    finance_top_category_limit: int = Field(
        default=5, ge=1, le=20, alias="FINANCE_TOP_CATEGORY_LIMIT"
    )
    notebook_storage_path: str | None = Field(default=None, alias="NOTEBOOK_STORAGE_PATH")
    notebook_max_file_size_mb: int = Field(
        default=25, ge=1, le=100, alias="NOTEBOOK_MAX_FILE_SIZE_MB"
    )
    notebook_search_scan_limit: int = Field(
        default=500, ge=1, le=5000, alias="NOTEBOOK_SEARCH_SCAN_LIMIT"
    )
    notebook_recent_limit: int = Field(default=10, ge=1, le=50, alias="NOTEBOOK_RECENT_LIMIT")
    notebook_allowed_url_schemes: str = Field(
        default="http,https", alias="NOTEBOOK_ALLOWED_URL_SCHEMES"
    )
    task_default_priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = Field(
        default="NORMAL", alias="TASK_DEFAULT_PRIORITY"
    )
    task_default_reminder_minutes: int = Field(
        default=60, ge=1, le=40320, alias="TASK_DEFAULT_REMINDER_MINUTES"
    )
    task_date_only_reminder_time: str = Field(
        default="09:00",
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$",
        alias="TASK_DATE_ONLY_REMINDER_TIME",
    )
    task_recent_limit: int = Field(default=10, ge=1, le=50, alias="TASK_RECENT_LIMIT")
    ai_provider: Literal["openai"] | None = Field(default=None, alias="AI_PROVIDER")
    ai_model: str | None = Field(default=None, alias="AI_MODEL")
    ai_api_key: SecretStr | None = Field(default=None, alias="AI_API_KEY")
    ai_timeout_seconds: int = Field(default=30, ge=1, le=120, alias="AI_TIMEOUT_SECONDS")
    ai_max_retries: int = Field(default=2, ge=0, le=5, alias="AI_MAX_RETRIES")
    ai_action_confidence_threshold: float = Field(
        default=0.75, ge=0, le=1, alias="AI_ACTION_CONFIDENCE_THRESHOLD"
    )
    ai_max_requests_per_minute: int = Field(
        default=30, ge=1, le=120, alias="AI_MAX_REQUESTS_PER_MINUTE"
    )
    stt_provider: Literal["openai"] | None = Field(default=None, alias="STT_PROVIDER")
    stt_model: str | None = Field(default=None, alias="STT_MODEL")
    stt_api_key: SecretStr | None = Field(default=None, alias="STT_API_KEY")
    stt_max_file_size_mb: int = Field(default=20, ge=1, le=25, alias="STT_MAX_FILE_SIZE_MB")
    stt_timeout_seconds: int = Field(default=60, ge=1, le=180, alias="STT_TIMEOUT_SECONDS")
    assistant_context_ttl_seconds: int = Field(
        default=3600, ge=60, le=86400, alias="ASSISTANT_CONTEXT_TTL_SECONDS"
    )
    assistant_context_max_messages: int = Field(
        default=10, ge=1, le=50, alias="ASSISTANT_CONTEXT_MAX_MESSAGES"
    )
    reminder_default_offset_minutes: int = Field(
        default=10, ge=1, le=40320, alias="REMINDER_DEFAULT_OFFSET_MINUTES"
    )
    reminder_max_attempts: int = Field(default=3, ge=1, le=10, alias="REMINDER_MAX_ATTEMPTS")
    reminder_retry_delays_seconds: str = Field(
        default="60,300,900", alias="REMINDER_RETRY_DELAYS_SECONDS"
    )
    reminder_overdue_grace_minutes: int = Field(
        default=60, ge=0, le=10080, alias="REMINDER_OVERDUE_GRACE_MINUTES"
    )
    reminder_processing_timeout_minutes: int = Field(
        default=10, ge=1, le=1440, alias="REMINDER_PROCESSING_TIMEOUT_MINUTES"
    )

    telegram_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_owner_id: int | None = Field(default=None, gt=0, alias="TELEGRAM_OWNER_ID")
    telegram_api_id: int | None = Field(default=None, gt=0, alias="TELEGRAM_API_ID")
    telegram_api_hash: SecretStr | None = Field(default=None, alias="TELEGRAM_API_HASH")

    database_url: SecretStr | None = Field(default=None, alias="DATABASE_URL")
    redis_url: SecretStr | None = Field(default=None, alias="REDIS_URL")
    secret_key: SecretStr | None = Field(default=None, alias="SECRET_KEY")
    bot_pin: SecretStr | None = Field(default=None, alias="BOT_PIN")
    bot_pin_hash: SecretStr | None = Field(default=None, alias="BOT_PIN_HASH")
    bot_unlock_max_attempts: int = Field(default=5, ge=1, le=20, alias="BOT_UNLOCK_MAX_ATTEMPTS")
    bot_unlock_lockout_seconds: int = Field(
        default=300, ge=1, le=86400, alias="BOT_UNLOCK_LOCKOUT_SECONDS"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
        validate_assignment=True,
        hide_input_in_errors=True,
    )

    @field_validator("app_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("APP_TIMEZONE must be a valid IANA timezone") from exc
        return value

    @field_validator("reminder_retry_delays_seconds")
    @classmethod
    def validate_retry_delays(cls, value: str) -> str:
        try:
            delays = tuple(int(item.strip()) for item in value.split(","))
        except ValueError:
            raise ValueError(
                "REMINDER_RETRY_DELAYS_SECONDS must be comma-separated integers"
            ) from None
        if not delays or any(delay < 1 or delay > 86400 for delay in delays):
            raise ValueError("Reminder retry delays must be between 1 and 86400 seconds")
        return ",".join(str(delay) for delay in delays)

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)

    @property
    def is_owner_configured(self) -> bool:
        return self.telegram_owner_id is not None and bool(self.telegram_bot_token)

    @property
    def reminder_retry_delays(self) -> tuple[int, ...]:
        return tuple(int(item) for item in self.reminder_retry_delays_seconds.split(","))

    @field_validator("notebook_allowed_url_schemes")
    @classmethod
    def validate_notebook_url_schemes(cls, value: str) -> str:
        schemes = tuple(item.strip().lower() for item in value.split(",") if item.strip())
        if not schemes or any(item not in {"http", "https"} for item in schemes):
            raise ValueError("NOTEBOOK_ALLOWED_URL_SCHEMES may contain only http and https")
        return ",".join(dict.fromkeys(schemes))

    @property
    def notebook_allowed_schemes(self) -> tuple[str, ...]:
        return tuple(self.notebook_allowed_url_schemes.split(","))

    @property
    def daily_morning_time(self) -> time:
        return time.fromisoformat(self.daily_morning_default_time)

    @property
    def daily_evening_time(self) -> time:
        return time.fromisoformat(self.daily_evening_default_time)


def get_settings() -> Settings:
    """Load explicitly at startup so imports have no configuration side effects."""
    return Settings()
