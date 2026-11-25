from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from models import User, db


def test_readiness_is_public_and_ready_with_no_users(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ready"}


def test_readiness_is_unavailable_when_users_table_is_missing(client):
    User.__table__.drop(db.engine)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.get_json() == {"status": "unavailable"}


@pytest.mark.parametrize("failure_point", ["connect", "execute"])
def test_readiness_handles_database_failure_and_recovers(client, monkeypatch, failure_point):
    failure = SQLAlchemyError("private database connection details")

    with monkeypatch.context() as patch:
        if failure_point == "connect":
            def fail_connect():
                raise failure

            patch.setattr(db.engine, "connect", fail_connect)
        else:
            connection = MagicMock()
            connection.execute.side_effect = failure
            context_manager = MagicMock()
            context_manager.__enter__.return_value = connection
            patch.setattr(db.engine, "connect", lambda: context_manager)

        response = client.get("/ready")

    assert response.status_code == 503
    assert response.get_json() == {"status": "unavailable"}
    assert client.get("/ready").status_code == 200
