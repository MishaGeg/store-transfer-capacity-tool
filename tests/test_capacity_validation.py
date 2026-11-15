import pytest
from sqlalchemy import text

from models import BrandCapacity, Store, db


@pytest.fixture(params=[None, 42])
def capacity_target(logged_in_client, request):
    store = Store(name="Capacity validation store", type="store")
    db.session.add(store)
    db.session.flush()
    if request.param is not None:
        db.session.add(BrandCapacity(
            store_id=store.id, brand="ECCOGEOXSTUDIO", capacity=request.param,
        ))
    db.session.commit()
    return logged_in_client, f"/capacities/{store.id}/ECCOGEOXSTUDIO", request.param


@pytest.mark.parametrize("payload", [
    {}, {"capacity": None}, {"capacity": True}, {"capacity": False},
    {"capacity": 10.5}, {"capacity": 10.0}, {"capacity": "10"},
    {"capacity": []}, {"capacity": {}},
])
def test_capacity_rejects_non_integer_values_without_changes(capacity_target, payload):
    client, url, original = capacity_target
    response = client.put(url, json=payload)
    assert response.status_code == 400
    assert response.get_json() == {"error": "capacity must be an integer"}
    row = BrandCapacity.query.one_or_none()
    if original is None:
        assert row is None
    else:
        assert row.capacity == original


def test_capacity_rejects_negative_integer_without_changes(capacity_target):
    client, url, original = capacity_target
    response = client.put(url, json={"capacity": -1})
    assert response.status_code == 400
    assert response.get_json() == {"error": "capacity cannot be negative"}
    row = BrandCapacity.query.one_or_none()
    if original is None:
        assert row is None
    else:
        assert row.capacity == original


@pytest.mark.parametrize("value", [0, 100])
def test_capacity_accepts_zero_and_positive_integers(capacity_target, value):
    client, url, _ = capacity_target
    response = client.put(url, json={"capacity": value})
    assert response.status_code == 200
    assert response.get_json() == {"brand": "ECCOGEOXSTUDIO", "capacity": value}
    assert BrandCapacity.query.one().capacity == value


def test_failed_capacity_commit_rolls_back_and_allows_retry(capacity_target, monkeypatch, caplog):
    client, url, original = capacity_target
    private_value = "private database parameter"

    def fail_commit():

        db.session.flush()
        db.session.execute(
            text("SELECT :value FROM missing_logging_test_table"),
            {"value": private_value},
        )

    with monkeypatch.context() as patch:
        patch.setattr(db.session, "commit", fail_commit)
        response = client.put(url, json={"capacity": 100})

    assert response.status_code == 500
    assert response.get_json() == {
        "error": "Could not save capacity. Please try again."
    }
    assert "private database parameter" not in response.get_data(as_text=True)
    assert "private database parameter" not in caplog.text
    assert "parameters hidden" in caplog.text
    records = [record for record in caplog.records if record.getMessage() == "Could not save capacity"]
    assert len(records) == 1
    assert records[0].exc_info is not None
    row = BrandCapacity.query.one_or_none()
    if original is None:
        assert row is None
    else:
        assert row.capacity == original

    assert client.put(url, json={"capacity": 100}).status_code == 200
    assert BrandCapacity.query.one().capacity == 100
