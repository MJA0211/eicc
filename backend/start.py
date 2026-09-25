"""Migrate, initialize the configured environment, then serve the API."""

import uvicorn
from alembic import command
from alembic.config import Config

from backend.seed import main

if __name__ == "__main__":
    command.upgrade(Config("alembic.ini"), "head")
    main()
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000)  # noqa: S104 -- private container network
