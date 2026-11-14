from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from crescendo_api.config import get_settings


def test_initial_migration_can_upgrade_and_downgrade(tmp_path, monkeypatch):
    # tmp_path supplies a disposable directory. Apply the actual migration rather
    # than creating tables from ORM metadata, which could hide a broken migration.
    monkeypatch.setenv("DEV_API_TOKEN", "migration-test-token-with-at-least-32-characters")
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    engine = create_engine(url)
    try:
        command.upgrade(config, "head")
        assert "runs" in inspect(engine).get_table_names()
        assert len(inspect(engine).get_check_constraints("runs")) == 5
        # Compare the migrated schema with ORM metadata to detect schema drift.
        command.check(config)
        # Exercise reversal only against this disposable test database.
        command.downgrade(config, "base")
        assert "runs" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
        get_settings.cache_clear()
