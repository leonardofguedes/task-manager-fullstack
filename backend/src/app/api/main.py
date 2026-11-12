from fastapi import FastAPI

from app.api.routers import health
from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Task Manager API", version="1.0.0")
    app.state.settings = settings
    app.include_router(health.router)
    return app
