from fastapi import FastAPI

from config.settings import get_settings
from molecules.exceptions import MoleculeError
from organisms.api.error_handlers import molecule_exception_handler
from organisms.api.routers.agents import router as agents_router
from organisms.api.routers.conversations import router as conversations_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

    # Health endpoint
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Register routers
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(agents_router, prefix="/api/v1")

    # Error handlers
    app.add_exception_handler(MoleculeError, molecule_exception_handler)  # type: ignore[arg-type]

    return app


app = create_app()
