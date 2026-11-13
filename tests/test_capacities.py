from datetime import datetime, timedelta

from catalog import get_brands_by_age_group, get_brand_age_group_pairs, get_brand_group, get_brand_group_names
from models import BrandCapacity, PlannedTransfer, StockSnapshot, Store, db


def add_store(name, store_type="store"):
    store = Store(name=name, type=store_type)
    db.session.add(store)
    db.session.commit()
    return store


def add_capacity(store, brand, capacity):
    row = BrandCapacity(store_id=store.id, brand=brand, capacity=capacity)
    db.session.add(row)
    db.session.commit()
    return row


def add_stock(store, brand, quantity, segment="ADULTS", category="FOOTWEAR"):
    row = StockSnapshot(
        store_id=store.id,
        brand=brand,
        category=category,
        segment=segment,
        quantity=quantity,
        snapshot_date=datetime.now(),
    )
    db.session.add(row)
    db.session.commit()
    return row


def add_transfer(source, destination, brand, quantity, segment="ADULTS", days_old=0):
    row = PlannedTransfer(
        from_store_id=source.id,
        to_store_id=destination.id,
        brand=brand,
        segment=segment,
        quantity=quantity,
        submitted_at=datetime.now() - timedelta(days=days_old),
    )
    db.session.add(row)
    db.session.commit()
    return row


def destination(payload, store_id):
    return next(store for store in payload["destinations"] if store["id"] == store_id)


def test_catalog_rules_describe_age_groups_and_shared_brand_groups():
    assert get_brand_group("ECCO", "ADULTS") == "ECCOGEOXSTUDIO"
    assert get_brand_group("ECCO", "KIDS") == "BATABAMBINO"
    assert get_brand_group("BATA", "KIDS") is None
    assert get_brands_by_age_group("ADULTS") == [
        "BATA", "ECCO", "GEOX", "REPLAY", "SCARPIERA", "STUDIO"
    ]
    assert get_brands_by_age_group("KIDS") == ["BAMB", "ECCO", "GEOX"]
    assert get_brand_group_names() == ["BATABAMBINO", "ECCOGEOXSTUDIO", "SCARPIERA"]
    assert set(get_brand_age_group_pairs("BATABAMBINO")) == {
        ("BATA", "ADULTS"),
        ("BAMB", "KIDS"),
        ("ECCO", "KIDS"),
        ("GEOX", "KIDS"),
    }


def test_capacity_list_includes_every_store_pool_and_preserves_zero(logged_in_client):
    alpha = add_store("Alpha")
    beta = add_store("Beta")
    add_capacity(alpha, "ECCOGEOXSTUDIO", 0)

    response = logged_in_client.get("/capacities")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "store_id": alpha.id,
            "store_name": "Alpha",
            "capacities": {
                "BATABAMBINO": None,
                "ECCOGEOXSTUDIO": 0,
                "SCARPIERA": None,
            },
        },
        {
            "store_id": beta.id,
            "store_name": "Beta",
            "capacities": {
                "BATABAMBINO": None,
                "ECCOGEOXSTUDIO": None,
                "SCARPIERA": None,
            },
        },
    ]


def test_capacity_update_creates_updates_and_rejects_invalid_input(logged_in_client):
    store = add_store("City Store")
    url = f"/capacities/{store.id}/ECCOGEOXSTUDIO"

    assert logged_in_client.put(url, json={"capacity": 42}).get_json() == {
        "brand": "ECCOGEOXSTUDIO",
        "capacity": 42,
    }
    assert logged_in_client.put(url, json={"capacity": 0}).get_json()["capacity"] == 0
    assert BrandCapacity.query.one().capacity == 0
    assert logged_in_client.put(url, json={"capacity": -1}).status_code == 400
    assert logged_in_client.put(url, json={"capacity": "many"}).status_code == 400
    assert logged_in_client.put(f"/capacities/{store.id}/GEOX", json={"capacity": 1}).status_code == 404
    assert logged_in_client.put("/capacities/999/ECCOGEOXSTUDIO", json={"capacity": 1}).status_code == 404


def test_transfer_options_calculate_free_space_for_selected_pool(logged_in_client):
    source = add_store("Source")
    destination_store = add_store("Destination")
    add_capacity(destination_store, "ECCOGEOXSTUDIO", 10000)
    add_stock(destination_store, "ECCO", 5000)
    add_stock(destination_store, "ECCO", 700, segment="KIDS")
    add_transfer(source, destination_store, "ECCO", 1000)

    response = logged_in_client.get("/transfer-options?brand=ECCO&segment=ADULTS")

    assert response.status_code == 200
    assert destination(response.get_json(), destination_store.id)["free_space"] == 4000


def test_transfer_options_combine_every_pair_in_a_shared_pool(logged_in_client):
    source = add_store("Source")
    destination_store = add_store("Destination")
    add_capacity(destination_store, "BATABAMBINO", 100)
    add_stock(destination_store, "BATA", 10)
    add_stock(destination_store, "BAMB", 15, segment="KIDS")
    add_stock(destination_store, "ECCO", 20, segment="KIDS")
    add_stock(destination_store, "GEOX", 5, segment="KIDS")
    add_stock(destination_store, "ECCO", 99)
    add_stock(destination_store, "BAMB", 50, segment="KIDS", category="SLIPPERS")
    add_transfer(source, destination_store, "BATA", 3)
    add_transfer(source, destination_store, "ECCO", 4, segment="KIDS")
    add_transfer(source, destination_store, "GEOX", 2, segment="KIDS")

    adults = logged_in_client.get("/transfer-options?brand=BATA&segment=ADULTS").get_json()
    kids = logged_in_client.get("/transfer-options?brand=BAMB&segment=KIDS").get_json()

    assert destination(adults, destination_store.id)["free_space"] == 41
    assert destination(kids, destination_store.id)["free_space"] == 41


def test_transfer_options_ignore_old_transfers(logged_in_client):
    source = add_store("Source")
    destination_store = add_store("Destination")
    add_capacity(destination_store, "ECCOGEOXSTUDIO", 10000)
    add_transfer(source, destination_store, "ECCO", 1000, days_old=6)

    payload = logged_in_client.get(
        "/transfer-options?brand=ECCO&segment=ADULTS"
    ).get_json()

    assert destination(payload, destination_store.id)["free_space"] == 10000


def test_transfer_options_use_exact_stock_for_sources_and_brand_group_for_destinations(logged_in_client):
    ecco_source = add_store("Ecco Source")
    geox_source = add_store("Geox Source")
    kids_destination = add_store("Kids Destination")
    adult_destination = add_store("Adult Destination")
    warehouse = add_store("Warehouse", "warehouse")
    add_stock(ecco_source, "ECCO", 4, segment="KIDS")
    add_stock(geox_source, "GEOX", 7, segment="KIDS")
    add_capacity(kids_destination, "BATABAMBINO", 100)
    add_capacity(adult_destination, "ECCOGEOXSTUDIO", 100)

    response = logged_in_client.get("/transfer-options?brand=ECCO&segment=KIDS")
    payload = response.get_json()

    assert response.status_code == 200
    assert {store["id"] for store in payload["sources"]} == {ecco_source.id, warehouse.id}
    assert {store["id"] for store in payload["destinations"]} == {
        kids_destination.id,
        warehouse.id,
    }
    assert destination(payload, kids_destination.id)["free_space"] == 100
    assert destination(payload, warehouse.id)["free_space"] is None


def test_transfer_options_reject_invalid_catalog_selection(logged_in_client):
    assert logged_in_client.get("/transfer-options?brand=BATA&segment=KIDS").status_code == 400
    assert logged_in_client.get("/transfer-options?brand=ECCO&segment=BABIES").status_code == 400


def test_transfer_page_embeds_catalog_and_removed_routes_are_gone(logged_in_client):
    page = logged_in_client.get("/transfers-page").get_data(as_text=True)

    assert "const BRANDS_BY_SEGMENT" in page
    assert '"BAMB"' in page
    assert "/transfer-options" in page
    assert "/catalog" not in page
    assert "/capacity-check" not in page
    assert logged_in_client.get("/catalog").status_code == 404
    assert logged_in_client.get("/capacity-check").status_code == 404
    assert logged_in_client.get("/capacity-groups").status_code == 404
    assert logged_in_client.get("/transfer-stores").status_code == 404
