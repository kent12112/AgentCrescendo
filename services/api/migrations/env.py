# Learn: From alembic, import context (the active Alembic migration configuration and transaction API).
from alembic import context
# Learn: From sqlalchemy, import create_engine (constructs a database connection-pool manager).
from sqlalchemy import create_engine

# Learn: From crescendo_api.config, import get_settings (loads and caches validated local configuration).
from crescendo_api.config import get_settings
# Learn: From crescendo_api.models, import Base (the SQLAlchemy registry whose metadata holds the table
# definitions).
from crescendo_api.models import Base


# Learn: Define run_migrations(). The body runs when called, not when defined.
def run_migrations():
    # Learn: Set url to get_settings().database_url; the destination or current page address.
    url = get_settings().database_url
    # Learn: Take this branch only if context.is_offline_mode().
    if context.is_offline_mode():
        # --sql renders migration SQL without connecting to the database.
        # Learn: Configure Alembic with this connection/URL and the model metadata on context.
        context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
        # Learn: Enter context.begin_transaction(). The context manager controls setup/exit; inspect it for
        # the actual cleanup behavior.
        with context.begin_transaction():
            # Learn: Execute or render the pending Alembic migration steps in this transaction on context.
            context.run_migrations()
        # Learn: Return None (no value) to the caller and stop this function.
        return
    # Online mode executes migrations against the configured database. Schema
    # changes happen explicitly here, not implicitly when the API starts.
    # Learn: Set engine to create_engine(url); the SQLAlchemy connection-pool manager, not a permanently
    # open transaction.
    engine = create_engine(url)
    # Learn: Enter engine.connect() as connection. The context manager controls setup/exit; inspect it for
    # the actual cleanup behavior.
    with engine.connect() as connection:
        # Learn: Configure Alembic with this connection/URL and the model metadata on context.
        context.configure(connection=connection, target_metadata=Base.metadata)
        # Learn: Enter context.begin_transaction(). The context manager controls setup/exit; inspect it for
        # the actual cleanup behavior.
        with context.begin_transaction():
            # Learn: Execute or render the pending Alembic migration steps in this transaction on context.
            context.run_migrations()
    # Learn: Call engine.dispose with no arguments.
    engine.dispose()


# Learn: Execute or render the pending Alembic migration steps in this transaction.
run_migrations()

