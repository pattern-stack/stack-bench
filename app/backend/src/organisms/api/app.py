from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.settings import get_settings
from molecules.exceptions import MoleculeError
from organisms.api.error_handlers import molecule_exception_handler
from organisms.api.routers.agents import router as agents_router
from organisms.api.routers.conversations import router as conversations_router
from organisms.api.routers.projects import router as projects_router
from organisms.api.routers.stacks import router as stacks_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — setup and teardown."""
    settings = get_settings()

    # Create engine and session factory
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Store on app state for DI
    app.state.engine = engine
    app.state.session_factory = session_factory

    yield

    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # Health endpoint
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Register routers
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(agents_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(stacks_router, prefix="/api/v1")

    # Error handlers
    app.add_exception_handler(MoleculeError, molecule_exception_handler)  # type: ignore[arg-type]

    return app


app = create_app()
