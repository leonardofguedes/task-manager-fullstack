from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.api.errors import register_error_handlers
from app.api.routers import auth, health, tasks, users
from app.config import Settings, get_settings
from app.infrastructure.db.session import make_engine, make_session_factory

API_PREFIX = "/api/v1"


def create_app(
    settings: Settings | None = None, session_factory: sessionmaker[Session] | None = None
) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Task Manager API",
        version="1.0.0",
        description="Task management REST API. Authenticate with the **Authorize** button "
        "(username = email). Demo users: alice@example.com / bob@example.com, password demo1234.",
    )
    app.state.settings = settings
    app.state.session_factory = session_factory or make_session_factory(
        make_engine(settings.database_url)
    )

    register_error_handlers(app)
    app.include_router(health.router)
    for router in (auth.router, users.router, tasks.router):
        app.include_router(router, prefix=API_PREFIX)
    return app
