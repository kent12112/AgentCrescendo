from alembic import context
from sqlalchemy import create_engine

from crescendo_api.config import get_settings
from crescendo_api.models import Base


def run_migrations():
    url = get_settings().database_url
    if context.is_offline_mode():
        # --sql renders migration SQL without connecting to the database.
        context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    # Online mode executes migrations against the configured database. Schema
    # changes happen explicitly here, not implicitly when the API starts.
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()

