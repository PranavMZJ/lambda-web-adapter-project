"""Unit tests for the Flask application (app/app.py).

Uses Flask test client with mocked DynamoDB via unittest.mock.
The app module reads DYNAMODB_TABLE_NAME at import time and creates a boto3
resource, so we must set the env var and mock boto3 before importing.
"""

import importlib
import json
import os
import sys

import pytest

# Ensure DYNAMODB_TABLE_NAME is set before any import of app.app
os.environ["DYNAMODB_TABLE_NAME"] = "test-table"
os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-1"

from unittest.mock import MagicMock, patch

# Mock boto3.resource before importing the app module so that the module-level
# `dynamodb = boto3.resource(...)` call uses our mock.
_mock_boto3_resource = patch("boto3.resource")
_mock_resource = _mock_boto3_resource.start()

mock_table = MagicMock()
_mock_resource.return_value.Table.return_value = mock_table

# Now it is safe to import the app module
import app.app as app_module  # noqa: E402

# Stop the patcher — the module-level objects are already bound to our mocks
_mock_boto3_resource.stop()


@pytest.fixture(autouse=True)
def _reset_mock_table():
    """Reset the mock table before each test."""
    mock_table.reset_mock()


@pytest.fixture()
def client():
    """Create a Flask test client."""
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


# ---- GET / ----

def test_health_check(client):
    """GET / returns 200 and {"status": "ok"}."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


# ---- POST /items ----

def test_create_item_valid(client):
    """POST /items with valid body returns 201 and the created item."""
    mock_table.put_item.return_value = {}

    resp = client.post(
        "/items",
        data=json.dumps({"name": "test-item"}),
        content_type="application/json",
    )

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "test-item"
    assert "id" in body
    assert "created_at" in body
    mock_table.put_item.assert_called_once()


def test_create_item_empty_body(client):
    """POST /items with empty body returns 400."""
    resp = client.post(
        "/items",
        data="",
        content_type="application/json",
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert "error" in body


def test_create_item_missing_name(client):
    """POST /items with missing name field returns 400."""
    resp = client.post(
        "/items",
        data=json.dumps({"description": "no name field"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert "error" in body


# ---- GET /items/<id> ----

def test_get_item_existing(client):
    """GET /items/<id> for an existing item returns 200."""
    mock_table.get_item.return_value = {
        "Item": {"id": "abc-123", "name": "found-item", "created_at": "2025-01-01T00:00:00Z"}
    }

    resp = client.get("/items/abc-123")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == "abc-123"
    assert body["name"] == "found-item"


def test_get_item_not_found(client):
    """GET /items/<id> for a non-existent item returns 404."""
    mock_table.get_item.return_value = {}

    resp = client.get("/items/nonexistent-id")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["error"] == "Item not found"


# ---- GET /items ----

def test_get_items_returns_list(client):
    """GET /items returns 200 with a JSON array."""
    mock_table.scan.return_value = {
        "Items": [
            {"id": "1", "name": "item-a", "created_at": "2025-01-01T00:00:00Z"},
            {"id": "2", "name": "item-b", "created_at": "2025-01-02T00:00:00Z"},
        ]
    }

    resp = client.get("/items")
    assert resp.status_code == 200
    body = resp.get_json()
    assert isinstance(body, list)
    assert len(body) == 2
