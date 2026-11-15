# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Application assembly. Run with uvicorn crescendo_api.main:app."""
# Learn: From fastapi, import FastAPI (creates the ASGI application and its schema-aware routing).
from fastapi import FastAPI

# Learn: From .routes, import runs (the persisted-draft route module registered by the application); system
# (the health/capability route module registered by the application).
from .routes import runs, system

# Learn: Set app to FastAPI(title='AgentCrescendo', version='0.1.0').
app = FastAPI(title="AgentCrescendo", version="0.1.0")
# Learn: Call app.include_router with the arguments shown.
app.include_router(system.router)
# Learn: Call app.include_router with the arguments shown.
app.include_router(runs.router)
