"""Application assembly. Run with uvicorn crescendo_api.main:app."""
# Import from fastapi: FastAPI (creates the ASGI application and its schema-aware routing).
from fastapi import FastAPI

# Import from .routes: runs (the persisted-draft route module registered by the application); system
# (the health/capability route module registered by the application).
from .routes import runs, system

# Set app to FastAPI(title='AgentCrescendo', version='0.1.0').
app = FastAPI(title="AgentCrescendo", version="0.1.0")
# Call app.include_router with system.router.
app.include_router(system.router)
# Call app.include_router with runs.router.
app.include_router(runs.router)
