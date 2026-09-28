import asyncio
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fakeredis.aioredis import FakeRedis
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.calendar.actions import CalendarActions
from app.modules.calendar.exceptions import (
    CalendarConfigurationError,
    CalendarError,
    OAuthStateError,
)
from app.modules.calendar.oauth import GoogleOAuthService
from app.modules.calendar.state import MemoryTemporaryStore, RedisTemporaryStore
from app.modules.security.lock_service import LockService


def oauth(http: httpx.AsyncClient) -> GoogleOAuthService:
    settings = Settings(
        _env_file=None,
        GOOGLE_CLIENT_ID="test-client",
        GOOGLE_CLIENT_SECRET="test-secret",
        GOOGLE_REDIRECT_URI="http://127.0.0.1:8000/oauth/google/callback",
        TELEGRAM_OWNER_ID=42,
    )
    store = Mock(
        save=AsyncMock(), load=AsyncMock(return_value=SecretStr("refresh")), delete=AsyncMock()
    )
    return GoogleOAuthService(
        settings, store, MemoryTemporaryStore(), LockService(), Mock(record=AsyncMock()), http
    )


def test_optional_google_settings() -> None:
    settings = Settings(
        _env_file=None,
        GOOGLE_CLIENT_ID=None,
        GOOGLE_CLIENT_SECRET=None,
        GOOGLE_REDIRECT_URI=None,
        DATA_ENCRYPTION_KEY=None,
    )
    assert settings.app_timezone == "Asia/Tashkent"
    assert settings.google_client_id is None


async def test_missing_config_fails_only_on_oauth() -> None:
    async with httpx.AsyncClient() as http:
        service = oauth(http)
        service.settings.google_client_id = None
        with pytest.raises(CalendarConfigurationError):
            await service.connect_url()


async def test_oauth_state_pkce_browser_binding_and_replay() -> None:
    async with httpx.AsyncClient() as http:
        service = oauth(http)
        await service.lock.unlock()
        link = await service.connect_url()
        ticket = parse_qs(urlsplit(link).query)["ticket"][0]
        url = await service.begin(ticket, "browser-random")
        query = parse_qs(urlsplit(url).query)
        assert query["access_type"] == ["offline"]
        assert query["code_challenge_method"] == ["S256"]
        assert len(query["state"][0]) >= 32
        assert "test-secret" not in url
        service.exchange = AsyncMock(return_value=SecretStr("private-token"))
        await service.callback(query["state"][0], "fake-code", "browser-random")
        service.store.save.assert_awaited_once_with(SecretStr("private-token"))
        with pytest.raises(OAuthStateError):
            await service.callback(query["state"][0], "fake-code", "browser-random")
        with pytest.raises(OAuthStateError):
            await service.begin(ticket, "browser-random")


@pytest.mark.parametrize("scenario", ["invalid", "browser", "locked"])
async def test_oauth_rejects_invalid_callback(scenario) -> None:
    async with httpx.AsyncClient() as http:
        service = oauth(http)
        await service.lock.unlock()
        ticket = parse_qs(urlsplit(await service.connect_url()).query)["ticket"][0]
        state = parse_qs(urlsplit(await service.begin(ticket, "correct")).query)["state"][0]
        service.exchange = AsyncMock()
        if scenario == "locked":
            await service.lock.lock()
        with pytest.raises(OAuthStateError):
            await service.callback(
                "invalid" if scenario == "invalid" else state,
                "fake-code",
                "wrong" if scenario == "browser" else "correct",
            )
        service.exchange.assert_not_called()


async def test_state_expiry(monkeypatch) -> None:
    store = MemoryTemporaryStore()
    monkeypatch.setattr("app.modules.calendar.state.time.monotonic", lambda: 100)
    token = await store.issue("oauth", {"test": True}, ttl=600)
    monkeypatch.setattr("app.modules.calendar.state.time.monotonic", lambda: 701)
    assert await store.consume("oauth", token) is None


async def test_redis_state_single_use_and_ttl() -> None:
    async with FakeRedis(decode_responses=True) as redis:
        store = RedisTemporaryStore(redis, "test", 42)
        token = await store.issue("oauth", {"owner": 42})
        assert 0 < await redis.ttl(store.key("oauth", token)) <= 600
        values = await asyncio.gather(store.consume("oauth", token), store.consume("oauth", token))
        assert values.count(None) == 1
        assert {"owner": 42} in values


async def test_create_confirmation_single_use_and_delete() -> None:
    service = Mock(create_event=AsyncMock(), delete_event=AsyncMock())
    actions = CalendarActions(service, Mock(unlocked=AsyncMock()), MemoryTemporaryStore(), 42)
    data = {
        "title": "Test",
        "start": "2026-09-25T15:00:00+05:00",
        "end": "2026-09-25T16:00:00+05:00",
    }
    token = await actions.prepare("create", data)
    service.create_event.assert_not_called()
    results = await asyncio.gather(
        actions.confirm(token), actions.confirm(token), return_exceptions=True
    )
    service.create_event.assert_awaited_once()
    assert sum(isinstance(item, CalendarError) for item in results) == 1
    token = await actions.prepare("delete", {"id": "abc", "etag": "v1"})
    service.delete_event.assert_not_called()
    await actions.confirm(token)
    service.delete_event.assert_awaited_once_with("abc", "v1")


async def test_disconnect_removes_credentials_on_revocation_outage() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(503))
    ) as http:
        service = oauth(http)
        assert not await service.disconnect()
        service.store.delete.assert_awaited_once()


async def test_oauth_http_endpoints_are_safe() -> None:
    from app.api.app import create_app
    from app.core.application import ApplicationContext

    context = ApplicationContext(
        Settings(
            _env_file=None,
            DATABASE_URL=None,
            REDIS_URL=None,
            SECURITY_STATE_BACKEND="memory",
            OAUTH_STATE_BACKEND="memory",
        )
    )
    await context.start()
    app = create_app(context=context)
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            response = await client.get("/oauth/google/start", params={"ticket": "x" * 32})
            assert response.status_code == 400
            assert response.headers["cache-control"] == "no-store"
            assert "Traceback" not in response.text
            response = await client.get(
                "/oauth/google/callback", params={"state": "x" * 32, "code": "secret-code" * 500}
            )
            assert response.status_code == 400
            assert "secret-code" not in response.text
    finally:
        await context.close()


async def test_oauth_http_cookie_and_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.app import create_app
    from app.core.application import ApplicationContext

    context = ApplicationContext(
        Settings(
            _env_file=None,
            DATABASE_URL=None,
            REDIS_URL=None,
            SECURITY_STATE_BACKEND="memory",
            OAUTH_STATE_BACKEND="memory",
        )
    )
    await context.start()
    app = create_app(context=context)
    try:
        context.calendar.oauth.begin = AsyncMock(
            return_value="https://accounts.google.com/o/oauth2/auth"
        )
        context.calendar.oauth.callback = AsyncMock()
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            response = await client.get("/oauth/google/start", params={"ticket": "x" * 32})
            assert response.status_code == 303
            assert "HttpOnly" in response.headers["set-cookie"]
            assert "SameSite=lax" in response.headers["set-cookie"]
            browser = client.cookies["calendar_oauth"]
            response = await client.get(
                "/oauth/google/callback", params={"state": "s" * 32, "code": "secret-code"}
            )
            assert response.status_code == 200 and "connected" in response.text
            context.calendar.oauth.callback.assert_awaited_once_with(
                "s" * 32, "secret-code", browser
            )
            assert "calendar_oauth" not in client.cookies
    finally:
        await context.close()


@pytest.mark.parametrize("scope_as_list", [True, False])
async def test_official_flow_exchange_scope_formats(scope_as_list: bool) -> None:
    from app.modules.calendar.auth import SCOPES

    async with httpx.AsyncClient() as http:
        service = oauth(http)
        flow = Mock()
        flow.fetch_token.return_value = {
            "refresh_token": "private-refresh",
            "scope": SCOPES if scope_as_list else " ".join(SCOPES),
        }
        service.flow = Mock(return_value=flow)
        assert (
            await service.exchange("code", "state", "verifier")
        ).get_secret_value() == "private-refresh"
        flow.fetch_token.assert_called_once_with(code="code", timeout=15)
        flow.oauth2session.close.assert_called_once()
