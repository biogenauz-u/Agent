# Stage 1 Step 1 - Complete File Contents

All paths are relative to C:/Users/USER/Documents/Agent.
The two __init__.py files are preserved unchanged.

## Runtime Verification

Python 3.12.10 was installed for the current Windows user through winget.
A project .venv was created and the project installed with its dev dependencies.
The .env file was created from .env.example with integration secrets unset.

- Configuration check: PASS; Asia/Tashkent resolved successfully.
- compileall app scripts: PASS.
- pytest -v: 16 passed.
- ruff check app scripts tests: PASS.
- pip check: no broken requirements.

Use .\.venv\Scripts\python.exe in the current terminal. Restart VS Code to pick up
the Python installation's PATH changes. Stage 1 Step 1 runtime verification is complete.

## pyproject.toml

````toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "personal-ai-assistant"
version = "0.1.0"
description = "Private personal AI assistant backend and Telegram bot foundation"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "aiogram>=3.13.0,<4",
    "sqlalchemy>=2.0.0,<3",
    "asyncpg>=0.29.0",
    "alembic>=1.14.0",
    "redis>=5.0.0",
    "pydantic>=2.9.2,<3",
    "pydantic-settings>=2.7.1,<3",
    "structlog>=24.4.0",
    "python-dotenv>=1.0.1",
    "argon2-cffi>=23.1.0",
    "tzdata>=2024.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.2",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.6.0",
]

[tool.setuptools.packages.find]
include = ["app", "app.*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"
````

## .gitignore

````text
node_modules/
.env
.env.*
!.env.example
.venv/
venv/
env/
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
.ruff_cache/
.pyright/
.coverage
.coverage.*
htmlcov/
coverage.xml
.idea/
.vscode/
*.log
Thumbs.db
dist/
build/
*.egg-info/
npm-debug.log*
.DS_Store
````

## .env.example

````text
APP_ENV=development
APP_DEBUG=true
APP_TIMEZONE=Asia/Tashkent
LOG_LEVEL=INFO

TELEGRAM_BOT_TOKEN=
TELEGRAM_OWNER_ID=
TELEGRAM_API_ID=
TELEGRAM_API_HASH=

# Configure service URLs when their features are implemented.
DATABASE_URL=
REDIS_URL=

# Supply a cryptographically random secret before enabling authentication.
SECRET_KEY=
# Configure a strong private PIN when the lock feature is implemented.
BOT_PIN=
````

## README.md

````markdown
# Personal AI Assistant

## Stage 1 - Step 1

A private Telegram assistant built incrementally. Only project configuration is
implemented: environment loading, masked secrets, timezone validation, a safe
verification script and isolated configuration tests.

## Technology Stack

Python 3.12+, Pydantic v2, pydantic-settings and tzdata form the foundation.
Dependencies for subsequent Stage 1 steps include FastAPI, Uvicorn, Aiogram 3,
SQLAlchemy 2 async, asyncpg, Alembic, Redis, structlog and Argon2.
Development tools: pytest, pytest-asyncio, HTTPX and Ruff.

## Windows Requirements and Installation

Use PowerShell in VS Code or Visual Studio. Python 3.12 is the recommended baseline;
Python 3.12 or newer is required. Install it from the official Windows downloads
page (https://www.python.org/downloads/windows/) or Microsoft Store.
With the classic official installer, enable **Add python.exe to PATH** and the
launcher if offered. Reopen your terminal afterward.

```powershell
Set-Location C:\Users\USER\Documents\Agent
python --version
py --version
```

At least one must report Python 3.12+. If `python` opens the Store, check Windows
App execution aliases and PATH. If the launcher is absent, use `python` instead of
`py -3.12` below after checking its version.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python scripts/check_config.py
python -m compileall app scripts
python -m pytest
python -m ruff check app scripts tests
```

If activation is blocked, optionally allow local scripts for this terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Alternatively, skip activation and use `.\.venv\Scripts\python.exe` for every Python
command. Run from the repository root. Editable installation is required before
running `python scripts/check_config.py` so imports work reliably.

### Linux Differences

Install Python 3.12+ and its venv package using your distribution's package manager.

```bash
python3 -m venv .venv
source .venv/bin/activate
test -f .env || cp .env.example .env
```

The remaining pip, verification and test commands are the same.

## Configuration

Environment variables override `.env`, which overrides safe defaults. Names are
case-insensitive. Empty environment and dotenv values are ignored; optional fields
default to None. Malformed nonempty numeric IDs fail validation; IDs must be positive.
Unknown dotenv keys are ignored for future compatibility.

| Variable | Purpose / default |
| --- | --- |
| APP_ENV | Environment label; development |
| APP_DEBUG | Debug flag; false in code, true in example |
| APP_TIMEZONE | IANA timezone; Asia/Tashkent |
| LOG_LEVEL | Future logging configuration; INFO |
| TELEGRAM_OWNER_ID | Optional positive owner ID |
| TELEGRAM_BOT_TOKEN | Optional secret bot credential |
| TELEGRAM_API_ID / TELEGRAM_API_HASH | Optional future MTProto credentials |
| DATABASE_URL / REDIS_URL | Optional secret service URLs |
| SECRET_KEY | Optional secret, no usable default |
| BOT_PIN | Optional secret, no default PIN |

Call `get_settings()` or `Settings()` explicitly at startup. Importing the module
does not load settings. `timezone` returns ZoneInfo; tzdata supplies the timezone
database on Windows. Future timestamps must be timezone-aware, stored in UTC and
presented in the configured timezone.

Loading with integrations unset is allowed. Each future feature must validate its
required credentials at startup. Secret URLs are masked strings, not yet validated
connection URLs. The verification script prints non-sensitive settings and configured
booleans only. Invalid configuration returns exit code 1 with field names, without
input values. Tests isolate environment variables and never read your real `.env`.

## Current Structure

```text
Agent/
  app/
    __init__.py
    core/
      __init__.py
      config.py
  scripts/
    check_config.py
  tests/
    test_config.py
  .env.example
  .gitignore
  pyproject.toml
  README.md
```

Existing package.json, package-lock.json and server.js are retained legacy Node.js
files. They are not used by this Python application. Package discovery includes
only app and its subpackages. No additional empty directories are required now.

## Planned Stage 1 Structure

```text
app/
  main.py                 FastAPI composition and lifespan
  core/                   Configuration, security, logging and constants
  database/models/        Async sessions and ORM models
  bot/                    Bot and dispatcher composition
    middlewares/          Owner authorization, lock and error handling
    filters/              Reusable update filters
    handlers/             Thin command adapters
    keyboards/            Telegram menus
  modules/
    users/                Owner repository and service
    audit/                Audit repository and service
  services/               Shared services and integration boundaries
  api/routes/             HTTP endpoints and health checks
migrations/               Alembic revisions
tests/                    Unit and integration tests
docker/                   Container support when needed
Dockerfile
docker-compose.yml
alembic.ini
```

Calendar, reminders, email, finance, notebook, tasks, personal Telegram, AI, voice
and storage modules will be added when their contracts are defined. Handlers and
routes will delegate business logic to services. AI output must become a structured
action validated and authorized by the backend, with confirmation when required.

## Security Notes

- Secrets come from environment variables; dotenv files are ignored by Git.
- SecretStr masks tokens, PINs, keys and URLs; it is not encryption.
- Never log full Settings objects, raw secrets or validation input.
- Use get_secret_value() only at integration boundaries that need credentials.
- Configure a strong PIN later; hashing, rate limits and session locking are future work.
- Features must fail closed when required credentials or authorization are missing.
- Dependency constraints are not a reproducible deployment lockfile.

## Not Implemented Yet

FastAPI server, health endpoints, Telegram handlers, owner middleware, database and
Redis connections, ORM models, audit persistence, locks, Docker, migrations,
encryption, TOTP and future product modules are not implemented in this step.

## Next Development Step

Run configuration verification and tests successfully before starting the agreed
Stage 1 Step 2 scope. This step implements configuration only.
````

## app/__init__.py

````python
"""Application package for the Personal AI Assistant project."""
````

## app/core/__init__.py

````python
"""Core application configuration and shared utilities."""
````

## app/core/config.py

````python
from __future__ import annotations

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

    telegram_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_owner_id: int | None = Field(default=None, gt=0, alias="TELEGRAM_OWNER_ID")
    telegram_api_id: int | None = Field(default=None, gt=0, alias="TELEGRAM_API_ID")
    telegram_api_hash: SecretStr | None = Field(default=None, alias="TELEGRAM_API_HASH")

    database_url: SecretStr | None = Field(default=None, alias="DATABASE_URL")
    redis_url: SecretStr | None = Field(default=None, alias="REDIS_URL")
    secret_key: SecretStr | None = Field(default=None, alias="SECRET_KEY")
    bot_pin: SecretStr | None = Field(default=None, alias="BOT_PIN")

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

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)

    @property
    def is_owner_configured(self) -> bool:
        return self.telegram_owner_id is not None and bool(self.telegram_bot_token)


def get_settings() -> Settings:
    """Load explicitly at startup so imports have no configuration side effects."""
    return Settings()
````

## scripts/check_config.py

````python
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
````

## tests/test_config.py

````python
"""Configuration tests never load the owner's .env or credentials."""

import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    names = {str(field.alias).upper() for field in Settings.model_fields.values()}
    for name in list(os.environ):
        if name.upper() in names:
            monkeypatch.delenv(name)


def test_optional_ids_and_default_timezone() -> None:
    settings = Settings(_env_file=None)
    assert settings.telegram_owner_id is None
    assert settings.telegram_api_id is None
    assert not settings.is_owner_configured
    assert settings.app_timezone == "Asia/Tashkent"
    assert datetime(2026, 1, 1, tzinfo=settings.timezone).utcoffset() == timedelta(hours=5)


def test_empty_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for field in Settings.model_fields.values():
        monkeypatch.setenv(str(field.alias), "")
    settings = Settings(_env_file=None)
    assert settings.telegram_owner_id is None
    assert settings.telegram_api_id is None
    assert settings.bot_pin is None
    assert settings.database_url is None


def test_example_file_loads() -> None:
    example = Path(__file__).resolve().parents[1] / ".env.example"
    settings = Settings(_env_file=example)
    assert settings.telegram_owner_id is None
    assert settings.telegram_api_id is None
    assert settings.secret_key is None


@pytest.mark.parametrize("name", ["TELEGRAM_OWNER_ID", "TELEGRAM_API_ID"])
@pytest.mark.parametrize("value", ["abc", "0", "-1"])
def test_invalid_ids(name: str, value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_TIMEZONE", "Invalid/Timezone")
    with pytest.raises(ValidationError, match="IANA timezone"):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "name",
    ["telegram_bot_token", "telegram_api_hash", "bot_pin", "secret_key",
     "database_url", "redis_url"],
)
def test_secrets_masked(name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    value = "test-only-sensitive-value"
    monkeypatch.setenv(name.upper(), value)
    settings = Settings(_env_file=None)
    secret = getattr(settings, name)
    assert isinstance(secret, SecretStr)
    assert secret.get_secret_value() == value
    assert value not in str(settings)
    assert value not in repr(settings)
    assert value not in settings.model_dump_json()
````
