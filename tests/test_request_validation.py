from io import BytesIO

import pytest

from models import BrandCapacity, PlannedTransfer, StockSnapshot, Store, db


@pytest.fixture
def transfer_request(logged_in_client):
    source = Store(name="Validated source", type="store")
    destination = Store(name="Validated destination", type="warehouse")
    db.session.add_all([source, destination])
    db.session.commit()
    return logged_in_client, {
        "brand": "ECCO", "segment": "ADULTS", "quantity": 2,
        "from_store_id": source.id, "to_store_id": destination.id,
    }


INVALID_TRANSFER_FIELDS = [
    (field, value, "store IDs must be integers")
    for field in ("from_store_id", "to_store_id")
    for value in ("1", True, None, [], {}, 1.5)
] + [
    (field, value, "source or destination store does not exist")
    for field in ("from_store_id", "to_store_id")
    for value in (-1, 0, 2_147_483_648, 10**100, 999999)
] + [
    ("quantity", value, "quantity must be an integer")
    for value in ("2", True, None, [], {}, 2.5)
] + [
    ("quantity", value, "quantity must be between 1 and 2147483647")
    for value in (-1, 0, 2_147_483_648)
] + [
    ("segment", value, "segment must be ADULTS or KIDS")
    for value in (None, [], {}, True, 123, "BAD")
]


@pytest.mark.parametrize("field,value,error", INVALID_TRANSFER_FIELDS)
def test_invalid_transfer_fields_do_not_abort_valid_rows(transfer_request, field, value, error):
    client, valid = transfer_request
    response = client.post("/transfers", json={"transfers": [
        {**valid, field: value}, valid,
    ]})
    assert response.status_code == 207
    assert response.get_json()["errors"] == [{"index": 0, "error": error}]
    assert len(response.get_json()["created"]) == 1
    assert PlannedTransfer.query.one().quantity == 2


@pytest.mark.parametrize("row", [None, [], 123, "invalid"])
def test_non_object_transfer_rows_are_rejected(transfer_request, row):
    client, valid = transfer_request
    response = client.post("/transfers", json={"transfers": [row, valid]})
    assert response.status_code == 207
    assert response.get_json()["errors"] == [{"index": 0, "error": "row must be an object"}]
    assert PlannedTransfer.query.count() == 1


def test_same_store_is_rejected_before_saving(transfer_request):
    client, valid = transfer_request
    response = client.post("/transfers", json={"transfers": [
        {**valid, "to_store_id": valid["from_store_id"]},
    ]})
    assert response.status_code == 400
    assert response.get_json()["errors"] == [{
        "index": 0, "error": "source and destination stores must differ",
    }]
    assert PlannedTransfer.query.count() == 0


def test_largest_database_quantity_is_accepted(transfer_request):
    client, valid = transfer_request
    response = client.post("/transfers", json={"transfers": [
        {**valid, "quantity": 2_147_483_647},
    ]})
    assert response.status_code == 201
    assert PlannedTransfer.query.one().quantity == 2_147_483_647


@pytest.mark.parametrize("store_id", [0, 2_147_483_648, 10**100])
def test_out_of_range_path_ids_return_not_found(logged_in_client, store_id):
    capacity = logged_in_client.put(
        f"/capacities/{store_id}/ECCOGEOXSTUDIO", json={"capacity": 1},
    )
    deletion = logged_in_client.delete(f"/transfers/{store_id}")
    assert capacity.status_code == 404
    assert deletion.status_code == 404
    assert BrandCapacity.query.count() == 0


def test_capacity_database_range_is_checked(logged_in_client):
    store = Store(name="Integer range store", type="store")
    db.session.add(store)
    db.session.commit()
    url = f"/capacities/{store.id}/ECCOGEOXSTUDIO"
    assert logged_in_client.put(url, json={"capacity": 2_147_483_647}).status_code == 200
    response = logged_in_client.put(url, json={"capacity": 2_147_483_648})
    assert response.status_code == 400
    assert response.get_json() == {"error": "capacity cannot exceed 2147483647"}
    assert BrandCapacity.query.one().capacity == 2_147_483_647


def test_login_rejects_oversized_username(client):
    response = client.post("/login", json={"username": "x" * 121, "password": "password"})
    assert response.status_code == 400
    assert response.get_json() == {"error": "Username cannot exceed 120 characters"}



def test_upload_rejects_missing_file_wrong_extension_and_oversized_request(logged_in_client):
    assert logged_in_client.post("/import-stock").status_code == 400
    assert logged_in_client.post("/import-stock", data={
        "file": (BytesIO(b"invalid"), "stock.csv"),
    }).status_code == 400
    response = logged_in_client.post("/import-stock", data={
        "file": (BytesIO(b"x" * (5 * 1024 * 1024)), "stock.xlsx"),
    })
    assert response.status_code == 413
    assert response.get_json() == {"error": "ფაილის ზომა აჭარბებს ლიმიტს"}
    assert StockSnapshot.query.count() == 0
