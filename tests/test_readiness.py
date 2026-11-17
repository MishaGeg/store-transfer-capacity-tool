from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from models import db


def test_readiness_is_public_and_queries_database(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ready"}


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
