"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from tg_typist import __version__
from tg_typist.bot.webhook import router as telegram_webhook_router
from tg_typist.db.session import create_async_engine, create_session_factory
from tg_typist.settings import Settings, load_settings

SERVICE_NAME = "tg-typist"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the ASGI application without contacting external services."""

    app_settings = settings or load_settings()
    app = FastAPI(title="Telegram Typist Bot", version=__version__)
    app.state.settings = app_settings
    if app_settings.database_url is not None:
        app.state.db_engine = create_async_engine(app_settings.database_url)
        app.state.session_factory = create_session_factory(app.state.db_engine)
    app.include_router(telegram_webhook_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Return non-secret process health metadata."""

        return {
            "status": "ok",
            "service": SERVICE_NAME,
            "version": __version__,
            "environment": app_settings.environment,
        }

    return app


app = create_app()
