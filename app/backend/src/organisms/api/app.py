import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pattern_stack.atoms.config import settings as ps_settings
from pattern_stack.atoms.jobs import Worker, get_job_queue
from pattern_stack.atoms.patterns import InvalidStateTransitionError
from pattern_stack.features.auth.exceptions import AuthError
from pattern_stack.organisms.api.auth_router import create_auth_router
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.settings import get_settings
from molecules.events.setup import (
    configure_subsystems,
    setup_event_handlers,
    teardown_event_handlers,
    teardown_subsystems,
)
from molecules.exceptions import MoleculeError
from molecules.providers.github_adapter import GitHubAPIError
from organisms.api.dependencies import get_db
from organisms.api.error_handlers import (
    auth_exception_handler,
    github_exception_handler,
    molecule_exception_handler,
    state_transition_handler,
)
from organisms.api.routers.agents import router as agents_router
from organisms.api.routers.auth import router as auth_router
from organisms.api.routers.conversations import router as conversations_router
from organisms.api.routers.events import router as events_router
from organisms.api.routers.jobs import router as jobs_router
from organisms.api.routers.onboarding import router as onboarding_router
from organisms.api.routers.projects import router as projects_router
from organisms.api.routers.stacks import router as stacks_router
from organisms.api.routers.tasks import router as tasks_router
from organisms.api.routers.workspaces import router as workspaces_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — setup and teardown."""
    settings = get_settings()

    # Wire our JWT_SECRET into pattern-stack's auth config
    ps_settings.JWT_SECRET_KEY = settings.JWT_SECRET

    # Create engine and session factory
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Store on app state for DI
    app.state.engine = engine
    app.state.session_factory = session_factory

    # Configure infrastructure subsystems (jobs, events, broadcast)
    configure_subsystems(settings, session_factory=session_factory)

    # Wire domain event handlers onto the bus
    setup_event_handlers()

    # Start job worker as background task
    queue = get_job_queue()
    worker = Worker(
        queue=queue,
        max_concurrent=settings.JOB_MAX_CONCURRENT,
        poll_interval=settings.JOB_POLL_INTERVAL,
    )
    worker_task = asyncio.create_task(worker.start())
    app.state.worker = worker
    app.state.worker_task = worker_task

    yield

    # Stop job worker gracefully
    await worker.stop(graceful=True)
    worker_task.cancel()

    # Clean up event handlers
    teardown_event_handlers()

    # Reset subsystem singletons
    teardown_subsystems()

    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # CORS — allow frontend origin with credentials for auth cookies/headers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_allow_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health endpoint
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Auth router (pattern-stack built-in)
    ps_auth_router = create_auth_router(
        get_session=get_db,
        prefix="/api/v1/auth",
    )
    app.include_router(ps_auth_router)

    # Register routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(agents_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(stacks_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(onboarding_router, prefix="/api/v1")
    app.include_router(workspaces_router, prefix="/api/v1")

    # Error handlers
    app.add_exception_handler(AuthError, auth_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(MoleculeError, molecule_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(GitHubAPIError, github_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(InvalidStateTransitionError, state_transition_handler)  # type: ignore[arg-type]

    return app


app = create_app()
