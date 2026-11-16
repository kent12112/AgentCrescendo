# Import from alembic: context (the active Alembic migration configuration and transaction API).
from alembic import context
# Import from sqlalchemy: create_engine (constructs a database connection-pool manager).
from sqlalchemy import create_engine

# Import from crescendo_api.config: get_settings (loads and caches validated local configuration).
from crescendo_api.config import get_settings
# Import from crescendo_api.models: Base (the SQLAlchemy registry whose metadata holds the table
# definitions).
from crescendo_api.models import Base


# Define run_migrations with no parameters.
def run_migrations():
    # Set url to get_settings().database_url.
    url = get_settings().database_url
    # Check whether context.is_offline_mode().
    if context.is_offline_mode():
        # --sql renders migration SQL without connecting to the database.
        # Call context.configure with no arguments.
        context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
        # Use context.begin_transaction(); leave the context and run its cleanup when this block
        # ends.
        with context.begin_transaction():
            # Call context.run_migrations with no arguments.
            context.run_migrations()
        # Return without a value.
        return
    # Online mode executes migrations against the configured database. Schema
    # changes happen explicitly here, not implicitly when the API starts.
    # Set engine to create_engine(url).
    engine = create_engine(url)
    # Use engine.connect() as connection; leave the context and run its cleanup when this block
    # ends.
    with engine.connect() as connection:
        # Call context.configure with no arguments.
        context.configure(connection=connection, target_metadata=Base.metadata)
        # Use context.begin_transaction(); leave the context and run its cleanup when this block
        # ends.
        with context.begin_transaction():
            # Call context.run_migrations with no arguments.
            context.run_migrations()
    # Call engine.dispose with no arguments.
    engine.dispose()


# Call run_migrations with no arguments.
run_migrations()

