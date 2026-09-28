import uvicorn

from app.api.app import create_app
from app.core.config import get_settings
from app.core.logging import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        create_app(settings),
        host=settings.api_host,
        port=settings.api_port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
