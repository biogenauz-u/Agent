"""Verify installed project configuration without displaying credentials."""

from pydantic import ValidationError

from app.core.config import get_settings


def main() -> int:
    try:
        settings = get_settings()
    except ValidationError as exc:
        print("Configuration validation failed. Check these fields:")
        for error in exc.errors(include_input=False, include_context=False):
            print("- " + ".".join(str(part) for part in error["loc"]))
        return 1

    print("Configuration loaded successfully.")
    print(f"Environment: {settings.app_env}")
    print(f"Debug: {settings.app_debug}")
    print(f"Timezone: {settings.timezone.key}")
    print(f"Telegram owner configured: {settings.telegram_owner_id is not None}")
    print(f"Telegram bot token configured: {bool(settings.telegram_bot_token)}")
    print(f"Database URL configured: {bool(settings.database_url)}")
    print(f"Redis URL configured: {bool(settings.redis_url)}")
    print(f"Secret key configured: {bool(settings.secret_key)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
