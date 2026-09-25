"""Start an isolated, migrated, genuinely seeded browser-test server."""

import os
import tempfile


def main():
    with tempfile.TemporaryDirectory(prefix="eicc-e2e-") as temporary:
        os.environ["EICC_DATABASE_URL"] = "sqlite:///" + temporary.replace("\\", "/") + "/e2e.db"
        os.environ["EICC_DEMO_MODE"] = "true"
        os.environ["EICC_SECURE_COOKIES"] = "false"
        os.environ["EICC_ALLOWED_ORIGINS"] = '["http://127.0.0.1:4173"]'
        import uvicorn
        from alembic import command
        from alembic.config import Config

        from backend.seed import main as seed_main

        command.upgrade(Config("alembic.ini"), "head")
        seed_main()
        uvicorn.run("backend.main:app", host="127.0.0.1", port=8001, log_level="warning")


if __name__ == "__main__":
    main()
