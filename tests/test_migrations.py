from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from backend.config import settings
from backend.db import make_engine


def test_migration_upgrade_downgrade_and_reupgrade(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    monkeypatch.setenv("EICC_DATABASE_URL", url)
    settings.cache_clear()
    try:
        config = Config("alembic.ini")
        command.upgrade(config, "head")
        engine = make_engine(url)
        assert "evidence_attachments" in inspect(engine).get_table_names()
        assert "contract_fingerprint" in {c["name"] for c in inspect(engine).get_columns("test_executions")}
        engine.dispose()
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        command.check(config)
    finally:
        settings.cache_clear()
