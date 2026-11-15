import pytest
from sqlalchemy.exc import SQLAlchemyError

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



def test_failed_capacity_commit_rolls_back_and_allows_retry(capacity_target, monkeypatch):
    client, url, original = capacity_target
    def fail_commit():
        db.session.flush()
        raise SQLAlchemyError("private database failure details")
    with monkeypatch.context() as patch:
        patch.setattr(db.session, "commit", fail_commit)
        response = client.put(url, json={"capacity": 100})
    assert response.status_code == 500
    assert response.get_json() == {"error": "Could not save capacity. Please try again."}
    row = BrandCapacity.query.one_or_none()
    if original is None:
        assert row is None
    else:
        assert row.capacity == original
    assert client.put(url, json={"capacity": 100}).status_code == 200
    assert BrandCapacity.query.one().capacity == 100
