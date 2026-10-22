from models import Store, db, PlannedTransfer

def test_create_transfer_empty_list(logged_in_client):
    response = logged_in_client.post("/transfers", json={"transfers": []})
    assert response.status_code == 400
    assert response.get_json() == {"created": [], "errors": []}

def test_create_transfer_missing_quantity(logged_in_client):
    response = logged_in_client.post(
        "/transfers",
        json={"transfers": [{"brand": "NIKE"}]},
    )

    assert response.status_code == 400
    assert len(response.get_json()["errors"]) == 1

def test_create_transfer_missing_quantity(logged_in_client):
    response = logged_in_client.post(
        "/transfers",
        json={"transfers": [{"brand": "NIKE"}]}
    )

    assert response.status_code == 400
    assert len(response.get_json()["errors"]) == 1

def test_mixed_payload_returns_207_and_saves_valid_row(logged_in_client):
    from_store = Store(name="from_store", type="store")
    to_store = Store(name="to_store", type="store")
    
    db.session.add_all([from_store,to_store])
    db.session.commit()
    response = logged_in_client.post(
            "/transfers",
            json={"transfers": [{
                "brand": "ECCO", "quantity": 120, "from_store_id": from_store.id, "to_store_id": to_store.id
            },
            {
                "brand": "ECCO",  "from_store_id": from_store.id, "to_store_id": to_store.id
            }]}
        )
    assert response.status_code == 207
    assert len(response.get_json()["errors"]) == 1
    assert len(response.get_json()["created"]) == 1
    db.session.rollback()
    assert PlannedTransfer.query.count() == 1


def test_transfer_rejects_boolean_quantity(logged_in_client):
    response = logged_in_client.post(
        "/transfers",
        json={"transfers": [{"brand": "ECCO", "quantity": True, "from_store_id": 1, "to_store_id": 2}]},
    )

    assert response.status_code == 400
    assert response.get_json()["errors"] == [{"index": 0, "error": "quantity must be an integer"}]


def test_transfer_list_and_delete_lifecycle(logged_in_client):
    source = Store(name="source", type="store")
    destination = Store(name="destination", type="warehouse")
    db.session.add_all([source, destination])
    db.session.commit()

    created = logged_in_client.post("/transfers", json={"transfers": [{
        "brand": "GEOX", "quantity": 12, "from_store_id": source.id, "to_store_id": destination.id,
    }]})
    
    assert created.status_code == 201

    transfer_id = created.get_json()["created"][0]["id"]

    assert logged_in_client.get("/transfers").get_json()[0]["id"] == transfer_id
    assert logged_in_client.delete(f"/transfers/{transfer_id}").get_json()["deleted_id"] == transfer_id
    assert logged_in_client.get("/transfers").get_json() == []


def test_delete_unknown_transfer_returns_not_found(logged_in_client):
    response = logged_in_client.delete("/transfers/9999")

    assert response.status_code == 404
    assert "error" in response.get_json()
