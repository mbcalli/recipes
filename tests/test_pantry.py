from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from recipes.api.main import app
from recipes.core.database import Base, get_db

# ---- In-memory SQLite test database ----
# Use a single shared connection so that create_all and session queries
# all see the same in-memory database.

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Keep a single connection open for the lifetime of the test so that
# the in-memory database persists across create_all() and session queries.
_connection = test_engine.connect()

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_connection)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=_connection)
    yield
    Base.metadata.drop_all(bind=_connection)


@pytest.fixture
def client(setup_test_db):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---- Tests ----

def test_pantry_initially_empty(client):
    response = client.get("/pantry")
    assert response.status_code == 200
    assert response.json() == []


def test_add_pantry_item(client):
    response = client.post(
        "/pantry",
        json={"name": "flour", "quantity": "2", "unit": "cups"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "flour"
    assert data["quantity"] == "2"
    assert data["unit"] == "cups"
    assert "id" in data


def test_list_pantry_items(client):
    client.post("/pantry", json={"name": "sugar", "quantity": "1", "unit": "kg"})
    client.post("/pantry", json={"name": "salt", "quantity": "500", "unit": "g"})

    response = client.get("/pantry")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    names = {item["name"] for item in items}
    assert "sugar" in names
    assert "salt" in names


def test_update_pantry_item_quantity(client):
    create_resp = client.post(
        "/pantry",
        json={"name": "milk", "quantity": "1", "unit": "litre"},
    )
    item_id = create_resp.json()["id"]

    patch_resp = client.patch(f"/pantry/{item_id}", json={"quantity": "2"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["quantity"] == "2"
    assert patch_resp.json()["unit"] == "litre"  # unit unchanged


def test_update_pantry_item_unit(client):
    create_resp = client.post(
        "/pantry",
        json={"name": "butter", "quantity": "250", "unit": "g"},
    )
    item_id = create_resp.json()["id"]

    patch_resp = client.patch(f"/pantry/{item_id}", json={"unit": "kg"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["unit"] == "kg"


def test_delete_pantry_item(client):
    create_resp = client.post(
        "/pantry",
        json={"name": "eggs", "quantity": "12", "unit": ""},
    )
    item_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/pantry/{item_id}")
    assert delete_resp.status_code == 204

    list_resp = client.get("/pantry")
    assert list_resp.json() == []


def test_delete_nonexistent_pantry_item(client):
    response = client.delete("/pantry/9999")
    assert response.status_code == 404


def test_update_nonexistent_pantry_item(client):
    response = client.patch("/pantry/9999", json={"quantity": "5"})
    assert response.status_code == 404


def test_add_pantry_item_without_unit(client):
    response = client.post("/pantry", json={"name": "water"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "water"
    assert data["quantity"] is None
    assert data["unit"] is None


def test_multiple_add_and_list(client):
    items = [
        {"name": "olive oil", "quantity": "500", "unit": "ml"},
        {"name": "pasta", "quantity": "1", "unit": "kg"},
        {"name": "tomatoes", "quantity": "6", "unit": ""},
    ]
    ids = []
    for item in items:
        resp = client.post("/pantry", json=item)
        assert resp.status_code == 201
        ids.append(resp.json()["id"])

    list_resp = client.get("/pantry")
    assert len(list_resp.json()) == 3

    # Delete one
    client.delete(f"/pantry/{ids[0]}")
    list_resp = client.get("/pantry")
    assert len(list_resp.json()) == 2
