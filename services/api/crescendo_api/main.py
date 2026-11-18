"""Application assembly. Run with uvicorn crescendo_api.main:app."""
# Import from fastapi: FastAPI (creates the ASGI application and its schema-aware routing).
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Import from .routes: runs (the persisted-draft route module registered by the application); system
# (the health/capability route module registered by the application).
from .routes import applications, jobs, letters, runs, system, writer
from .writer_service import close_writer_manager


@asynccontextmanager
async def lifespan(app):
    try:
        yield
    finally:
        close_writer_manager()

# Set app to FastAPI(title='AgentCrescendo', version='0.1.0').
app = FastAPI(title="AgentCrescendo", version="0.1.0", lifespan=lifespan)
# Call app.include_router with system.router.
app.include_router(system.router)
# Call app.include_router with runs.router.
app.include_router(runs.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(letters.router)
app.include_router(writer.router)
