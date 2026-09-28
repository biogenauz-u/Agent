"""Safe application errors that do not contain credentials."""


class DatabaseConfigurationError(ValueError):
    """Database initialization requires a valid PostgreSQL configuration."""


class AuditDetailsError(ValueError):
    """Audit details must be JSON data without sensitive fields."""


class TelegramConfigurationError(ValueError):
    """Telegram startup requires valid owner, token and PIN configuration."""


class RedisConfigurationError(ValueError):
    """Redis initialization requires a valid private service URL."""


class SecurityStateUnavailable(RuntimeError):
    """Shared security storage failed or a verification lease was lost."""
