from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import gmail_oauth, google_oauth, health, root
from app.core.application import ApplicationContext
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging


def create_app(
    settings: Settings | None = None,
    context: ApplicationContext | None = None,
) -> FastAPI:
    """Own lifespan in API mode, or borrow an already-started context in combined mode."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = context is None
        resources = (
            context if context is not None else ApplicationContext(settings or get_settings())
        )
        if owned:
            configure_logging(resources.settings.log_level)
            await resources.start()
        elif not resources.runtime.startup_complete:
            raise RuntimeError("Shared application context has not started.")
        app.state.context = resources
        try:
            yield
        finally:
            if owned:
                await resources.close()

    app = FastAPI(title="Personal AI Assistant", lifespan=lifespan, debug=False)
    app.include_router(root.router)
    app.include_router(health.router)
    app.include_router(google_oauth.router)
    app.include_router(gmail_oauth.router)
    return app
