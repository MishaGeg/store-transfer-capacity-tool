import re
import time

import pytest

from models import User, db


@pytest.fixture
def rate_client(client, monkeypatch):
    monkeypatch.setitem(client.application.config, "WTF_CSRF_ENABLED", True)
    clock = [time.time()]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    user = User(username="limit_user", role="supply_chain")
    user.set_password("correct-password")
    db.session.add(user)
    db.session.commit()
    with client.application.app_context():
        page = client.get("/login")
    token = re.search(
        r'<meta name="csrf-token" content="([^"]+)">',
        page.get_data(as_text=True),
    ).group(1)
    return client, token, clock


def attempt(client, token, password="wrong-password", address="192.0.2.1"):
    with client.application.app_context():
        return client.post(
            "/login",
            headers={"X-CSRFToken": token},
            json={"username": "limit_user", "password": password},
            environ_overrides={"REMOTE_ADDR": address},
        )


def test_eleventh_attempt_is_blocked_then_window_resets(rate_client):
    client, token, clock = rate_client
    for _ in range(10):
        assert attempt(client, token).status_code == 401

    blocked = attempt(client, token, password="correct-password")
    assert blocked.status_code == 429
    assert blocked.get_json() == {
        "error": "Too many login attempts. Please wait a minute and try again."
    }

    clock[0] += 61
    assert attempt(client, token, password="correct-password").status_code == 200


def test_successful_logins_also_count(rate_client):
    client, token, _ = rate_client
    for _ in range(10):
        assert attempt(client, token, password="correct-password").status_code == 200
    assert attempt(client, token, password="correct-password").status_code == 429


def test_ip_addresses_have_separate_counters(rate_client):
    client, token, _ = rate_client
    for _ in range(10):
        assert attempt(client, token).status_code == 401
    assert attempt(client, token).status_code == 429

    assert attempt(client, token, address="192.0.2.2").status_code == 401
    assert attempt(client, token).status_code == 429


def test_loading_login_page_does_not_use_post_limit(rate_client):
    client, token, _ = rate_client
    for _ in range(12):
        with client.application.app_context():
            assert client.get("/login").status_code == 200
    assert attempt(client, token, password="correct-password").status_code == 200
