from models import db, Store, BrandCapacity, StockSnapshot, PlannedTransfer
from datetime import datetime

def add_store(name, store_type="store"):
    store = Store(name=name, type=store_type)
    db.session.add(store)
    db.session.commit()
    return store

def add_brand_capacity(store, brand, capacity):
    brand_capacity = BrandCapacity(store_id=store.id, brand=brand, capacity=capacity)
    db.session.add(brand_capacity)
    db.session.commit()
    return brand_capacity

def add_stock(store, brand, category, quantity):
    stock = StockSnapshot(
        store_id=store.id,
        brand=brand,
        category=category,
        quantity=quantity,
        snapshot_date=datetime.now()
    )
    db.session.add(stock)
    db.session.commit()
    return stock

def add_transfer(from_store, to_store, brand, quantity):
    transfer = PlannedTransfer(
        from_store_id=from_store.id,
        to_store_id=to_store.id,
        brand=brand,
        quantity=quantity,
        submitted_at = datetime.now()
    )
    db.session.add(transfer)
    db.session.commit()
    return transfer


def test_capacity_check_free_space(logged_in_client):
    from_store = add_store("fromstore")
    to_store = add_store("tostore")
    add_stock(to_store, "ECCO", "FOOTWEAR", 5000)
    add_transfer(from_store, to_store, "ECCO", 1000) 
    add_brand_capacity(to_store, "ECCOGEOXSTUDIO", 10000)
    response = logged_in_client.get("/capacity-check")
    assert response.status_code == 200
    assert response.get_json()["tostore"]["ECCO"] == 4000

    








  

    