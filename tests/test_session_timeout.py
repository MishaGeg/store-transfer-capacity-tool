import time

import pytest

from models import User, db


@pytest.fixture
def timed_login(client, monkeypatch):
    clock = [time.time()]
    monkeypatch.setattr(time, "time", lambda: clock[0])

    user = User(username="timeout_user", role="supply_chain")
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/login",
        json={"username": "timeout_user", "password": "test-password"},
    )
    assert response.status_code == 200
    with client.session_transaction() as session:
        assert session.permanent

    return client, clock


def request_stores(client):

    with client.application.app_context():
        return client.get("/stores")


def test_session_expires_after_inactivity(timed_login):
    client, clock = timed_login
    lifetime = client.application.permanent_session_lifetime.total_seconds()

    clock[0] += lifetime + 1

    assert request_stores(client).status_code == 401


def test_requests_renew_session_lifetime(timed_login):
    client, clock = timed_login
    lifetime = client.application.permanent_session_lifetime.total_seconds()

    clock[0] += lifetime * 0.75
    assert request_stores(client).status_code == 200


    clock[0] += lifetime * 0.75
    assert request_stores(client).status_code == 200

    clock[0] += lifetime + 1
    assert request_stores(client).status_code == 401
