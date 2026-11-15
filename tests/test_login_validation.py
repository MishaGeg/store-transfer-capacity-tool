import json

import pytest


@pytest.mark.parametrize("body", [None, [], ["username"], "hello", 123, True])
def test_login_rejects_non_object_json(client, body):
    response = client.post(
        "/login", data=json.dumps(body), content_type="application/json",
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "JSON body must be an object"}
    assert client.get("/stores").status_code == 401


@pytest.mark.parametrize("body", ["", "{broken", "not-json"])
def test_login_rejects_missing_or_malformed_json(client, body):
    response = client.post("/login", data=body, content_type="application/json")
    assert response.status_code == 400
    assert response.get_json() == {"error": "JSON body must be an object"}


@pytest.mark.parametrize("field", ["username", "password"])
@pytest.mark.parametrize("value", [None, 123, True, [], {}])
def test_login_rejects_non_string_credentials(client, field, value):
    credentials = {"username": "testuser", "password": "test-password"}
    credentials[field] = value
    response = client.post("/login", json=credentials)
    assert response.status_code == 400
    assert response.get_json() == {"error": "Username and password must be strings"}
    assert client.get("/stores").status_code == 401


@pytest.mark.parametrize("credentials", [
    {"username": "", "password": "test-password"},
    {"username": "testuser", "password": ""},
    {"username": "", "password": ""},
])
def test_login_rejects_empty_credentials(client, credentials):
    response = client.post("/login", json=credentials)
    assert response.status_code == 400
    assert response.get_json() == {"error": "Username and password are required"}
