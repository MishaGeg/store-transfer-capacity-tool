import pytest

from models import BrandCapacity, PlannedTransfer, Store, db


@pytest.mark.parametrize("method,path", [
    ("PUT", "/capacities/{store_id}/ECCOGEOXSTUDIO"),
    ("POST", "/transfers"),
])
@pytest.mark.parametrize("body", [
    "null", "[]", '[{"capacity": 10}]', '"hello"', "123", "true",
    "", "{broken",
])
def test_json_endpoints_reject_invalid_bodies_without_changes(
    logged_in_client, method, path, body,
):
    store = Store(name="JSON validation store", type="store")
    db.session.add(store)
    db.session.flush()
    db.session.add(BrandCapacity(
        store_id=store.id, brand="ECCOGEOXSTUDIO", capacity=42,
    ))
    db.session.commit()

    response = logged_in_client.open(
        path.format(store_id=store.id), method=method,
        data=body, content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "JSON body must be an object"}
    assert BrandCapacity.query.one().capacity == 42
    assert PlannedTransfer.query.count() == 0
