from pathlib import Path

from models import StockSnapshot, Store, User, db
from seed import STORES


def test_sample_workbook_supports_the_readme_demo(logged_in_client):
    source_name = "ICR_Shoes"
    destination_name = "ICR_Shoes East_Point"
    expected_stock = {
        (source_name, "ECCO"): 40,
        (source_name, "BATA"): 20,
        (destination_name, "ECCO"): 10,
        (destination_name, "BATA"): 5,
        ("WH_Gamarj", "ECCO"): 30,
        ("WH_Gamarj", "BATA"): 15,
    }
    sample_names = {name for name, brand in expected_stock}
    for name, store_type in STORES:
        if name in sample_names:
            db.session.add(Store(name=name, type=store_type))
    db.session.commit()
    stores = {store.name: store for store in Store.query.all()}
    assert set(stores) == sample_names

    sample = Path(__file__).resolve().parents[1] / "samples" / "stock_sample.xlsx"
    with sample.open("rb") as workbook:
        response = logged_in_client.post(
            "/import-stock",
            data={"file": (workbook, sample.name)},
            content_type="multipart/form-data",
        )
    assert response.status_code == 200
    assert response.get_json() == {"processed": 6, "skipped": []}
    assert {
        (store.name, stock.brand): stock.quantity
        for stock, store in db.session.query(StockSnapshot, Store)
        .join(Store, StockSnapshot.store_id == Store.id).all()
    } == expected_stock
    assert all(
        stock.category == "FOOTWEAR" and stock.segment == "ADULTS"
        for stock in StockSnapshot.query.all()
    )

    source = stores[source_name]
    destination = stores[destination_name]
    response = logged_in_client.put(
        f"/capacities/{destination.id}/ECCOGEOXSTUDIO", json={"capacity": 100}
    )
    assert response.status_code == 200

    options_url = "/transfer-options?brand=ECCO&segment=ADULTS"
    response = logged_in_client.get(options_url)
    assert response.status_code == 200
    options = response.get_json()
    assert source.id in {store["id"] for store in options["sources"]}
    assert next(
        store["free_space"] for store in options["destinations"]
        if store["id"] == destination.id
    ) == 90

    response = logged_in_client.post("/transfers", json={"transfers": [{
        "brand": "ECCO", "segment": "ADULTS", "quantity": 5,
        "from_store_id": source.id, "to_store_id": destination.id,
    }]})
    assert response.status_code == 201
    created = response.get_json()["created"]
    assert response.get_json()["errors"] == []
    options = logged_in_client.get(options_url).get_json()
    assert next(
        store["free_space"] for store in options["destinations"]
        if store["id"] == destination.id
    ) == 85

    assert logged_in_client.post("/logout").status_code == 200
    assert logged_in_client.get("/view-transfers").status_code == 401

    manager = User(username="manager", role="store_manager")
    manager.set_password("test-password")
    db.session.add(manager)
    db.session.commit()
    assert logged_in_client.post("/login", json={
        "username": "manager", "password": "test-password",
    }).status_code == 200
    response = logged_in_client.get("/view-transfers")
    assert response.status_code == 200
    assert response.get_json() == [{
        **created[0], "from_store_name": source_name, "to_store_name": destination_name,
    }]
    assert logged_in_client.get("/transfers").status_code == 403
