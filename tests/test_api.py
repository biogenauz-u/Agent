from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.app import create_app
from app.core.application import ApplicationContext
from app.core.config import Settings
from app.core.exceptions import RedisConfigurationError, SecurityStateUnavailable


def settings(**kwargs: object) -> Settings:
    values = {
        "DATABASE_URL": None,
        "REDIS_URL": None,
        "TELEGRAM_BOT_TOKEN": None,
        "TELEGRAM_OWNER_ID": None,
        "SECURITY_STATE_BACKEND": "memory",
    }
    values.update(kwargs)
    return Settings(_env_file=None, **values)


def test_backend_config_validation() -> None:
    assert settings().security_state_backend == "memory"
    assert settings(SECURITY_STATE_BACKEND="redis").security_state_backend == "redis"
    with pytest.raises(ValidationError):
        settings(SECURITY_STATE_BACKEND="other")


async def test_redis_backend_requires_url() -> None:
    context = ApplicationContext(settings(SECURITY_STATE_BACKEND="redis"))
    with pytest.raises(RedisConfigurationError):
        await context.start()
    assert not context.runtime.startup_complete


async def test_redis_required_no_fallback() -> None:
    redis = Mock()
    redis.close = AsyncMock()
    with (
        patch("app.core.application.RedisManager", return_value=redis),
        patch("app.core.application.check_redis_health", new=AsyncMock(return_value=False)),
    ):
        context = ApplicationContext(
            settings(SECURITY_STATE_BACKEND="redis", REDIS_URL="redis://local")
        )
        with pytest.raises(SecurityStateUnavailable):
            await context.start()
        redis.close.assert_awaited_once()


async def test_root_live_degraded_ready() -> None:
    app = create_app(settings())
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/")).json() == {
                "name": "Personal AI Assistant",
                "status": "running",
            }
            assert (await client.get("/health/live")).json() == {"status": "alive"}
            health = await client.get("/health")
            assert health.status_code == 200
            assert health.json() == {
                "status": "degraded",
                "services": {
                    "application": "ok",
                    "database": "not_configured",
                    "redis": "not_configured",
                    "telegram": "not_configured",
                    "reminder_scheduler": "disabled",
                    "gmail": "not_configured",
                    "personal_telegram": "disabled",
                    "notebook_storage": "not_configured",
                    "daily_automation": "disabled",
                },
            }
            assert (await client.get("/health/ready")).json() == {"status": "ready"}
        assert app.state.context.runtime.startup_complete
    assert not app.state.context.runtime.startup_complete


@pytest.mark.parametrize("healthy", [True, False])
async def test_optional_dependency_health_truthful_and_no_secrets(healthy: bool) -> None:
    context = ApplicationContext(
        settings(TELEGRAM_BOT_TOKEN="test-secret-token", TELEGRAM_OWNER_ID=42)
    )
    await context.start()
    context.database = Mock()
    context.redis = Mock()
    app = create_app(context=context)
    with (
        patch("app.api.routes.health.check_database_health", new=AsyncMock(return_value=healthy)),
        patch("app.api.routes.health.check_redis_health", new=AsyncMock(return_value=healthy)),
    ):
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["services"]["database"] == ("ok" if healthy else "unavailable")
            assert response.json()["services"]["redis"] == ("ok" if healthy else "unavailable")
            assert response.json()["services"]["telegram"] == "configured"
            assert response.json()["status"] == ("ok" if healthy else "degraded")
            assert "test-secret-token" not in response.text
            assert "42" not in response.text
    assert context.runtime.startup_complete  # borrowed lifespan does not dispose owner resources
    await context.close()


async def test_required_dependency_failure_readiness() -> None:
    context = ApplicationContext(settings())
    await context.start()
    context.settings.security_state_backend = "redis"
    context.redis = Mock()
    app = create_app(context=context)
    with patch("app.api.routes.health.check_redis_health", new=AsyncMock(return_value=False)):
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            assert (await client.get("/health")).status_code == 503
            assert (await client.get("/health/ready")).status_code == 503
            assert (await client.get("/health/live")).status_code == 200
    await context.close()


async def test_personal_telegram_error_is_reported_without_secrets() -> None:
    context = ApplicationContext(settings())
    await context.start()
    context.runtime.personal_telegram = "error"
    app = create_app(context=context)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
        assert response.json()["services"]["personal_telegram"] == "error"
        assert "api_hash" not in response.text.lower()
        assert "session" not in response.text.lower()
    await context.close()


async def test_context_initializes_once_and_cleans_reverse_order() -> None:
    calls: list[str] = []
    db, redis = Mock(), Mock()
    db.dispose = AsyncMock(side_effect=lambda: calls.append("database"))
    redis.close = AsyncMock(side_effect=lambda: calls.append("redis"))
    with (
        patch("app.core.application.DatabaseManager", return_value=db),
        patch("app.core.application.RedisManager", return_value=redis),
    ):
        context = ApplicationContext(settings(DATABASE_URL="test-url", REDIS_URL="test-url"))
        await context.start()
        await context.start()
        db.initialize.assert_called_once()
        redis.initialize.assert_called_once()
        await context.close()
        await context.close()
        assert calls == ["redis", "database"]
