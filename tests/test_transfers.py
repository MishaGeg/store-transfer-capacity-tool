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
