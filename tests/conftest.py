import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from backend.db import Base, get_db, make_engine
from backend.main import app, login_attempts
from backend.seed import seed


@pytest.fixture
def database(tmp_path):
    postgres = os.environ.get("EICC_TEST_DATABASE_URL")
    admin = None
    if postgres:
        admin = make_engine(postgres)
        schema = "eicc_test_" + uuid.uuid4().hex
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = admin.execution_options(schema_translate_map={None: schema})
    else:
        engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        seed(db)
    yield factory
    if admin:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


@pytest.fixture
def client(database):
    def test_db():
        with database() as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    login_attempts.clear()
    with TestClient(app) as client:
        response = client.post("/api/auth/demo", json={"role": "admin"})
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def records(client):
    return {r["key"]: r for r in client.get("/api/workspace").json()["items"]}


def create(client, kind, **payload):
    response = client.post(f"/api/{kind}", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def move(client, item, status):
    response = client.post(f"/api/{item['kind']}/{item['id']}/transition", json={"status": status})
    assert response.status_code == 200, response.text
    return response.json()


def connect(client, source, target, relation="AFFECTS"):
    response = client.post(
        "/api/links", json={"source_id": source["id"], "target_id": target["id"], "relation": relation}
    )
    assert response.status_code == 201, response.text
    return response.json()


def update(client, item, **payload):
    latest = client.get(f"/api/{item['kind']}/{item['id']}").json()
    response = client.patch(
        f"/api/{item['kind']}/{item['id']}", json=payload, headers={"If-Match": str(latest["revision"])}
    )
    assert response.status_code == 200, response.text
    return response.json()
