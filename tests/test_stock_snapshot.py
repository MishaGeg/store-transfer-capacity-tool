from datetime import datetime

from models import StockSnapshot, Store, db
from stock_snapshot import validate_stock_data, write_stock_data

class FakeSheet:
    def __init__(self, rows):
        self.rows = rows

    def iter_rows(self, min_row, values_only):
        assert min_row == 2
        assert values_only is True
        return iter(self.rows)


def test_validate_stock_data_aggregates_valid_rows_and_reports_invalid_ones():
    sheet = FakeSheet([
        ("FOOTWEAR", None, None, "ECCO", "test_store", "ADULTS", 2),
        ("FOOTWEAR", None, None, "ECCO", "test_store", "ADULTS", "3"),
        ("SLIPPERS", None, None, "GEOX", "Missing", "ADULTS", 1),
        ("FOOTWEAR", None, None, "ECCO", "test_store", "KIDS", 8),
        ("FOOTWEAR", None, None, "ECCO", "test_store", "ADULTS", "bad"),
    ])

    processed, skipped, totals = validate_stock_data(sheet, {"test_store": 7})

    assert processed == 3
    assert totals == {(7, "ECCO", "FOOTWEAR", "ADULTS"): 5, (7, "ECCO", "FOOTWEAR", "KIDS"): 8}
    assert skipped == [
        {"row": 4, "reason": "არასწორი მაღაზია: Missing"},
        {"row": 6, "reason": "არასწორი რაოდენობა"},
    ]


def test_write_stock_data_creates_then_replaces_snapshot_quantity(client):
    store = Store(name="test_store", type="store")
    db.session.add(store)
    db.session.commit()

    key = (store.id, "ECCO", "FOOTWEAR", "ADULTS")
    write_stock_data({key: 10})
    first_updated_at = StockSnapshot.query.one().snapshot_date
    write_stock_data({key: 15})

    snapshot = StockSnapshot.query.one()
    assert snapshot.quantity == 15
    assert snapshot.snapshot_date >= first_updated_at

def test_write_stock_data_keeps_adult_and_kids_stock_separate(client):
    store = Store(name="segment_store", type="store")
    db.session.add(store)
    db.session.commit()
    write_stock_data({
        (store.id, "ECCO", "FOOTWEAR", "ADULTS"): 10,
        (store.id, "ECCO", "FOOTWEAR", "KIDS"): 4,
    })
    assert {(row.segment, row.quantity) for row in StockSnapshot.query.all()} == {("ADULTS", 10), ("KIDS", 4)}


def test_stock_read_apis_return_current_data_and_latest_timestamp(logged_in_client):
    store = Store(name="test_store", type="store")
    db.session.add(store)
    db.session.commit()
    snapshot = StockSnapshot(
        store_id=store.id, brand="ECCO", category="FOOTWEAR", quantity=9,
        snapshot_date=datetime(1991, 11, 2, 9, 00),
    )
    db.session.add(snapshot)
    db.session.commit()

    assert logged_in_client.get("/current-stock").get_json() == [{
        "store_id": store.id, "store_name": "test_store", "brand": "ECCO",
        "category": "FOOTWEAR", "segment": "ADULTS", "quantity": 9,
    }]
    assert logged_in_client.get("/last-stock-update").get_json() == {"last_updated": "02.11.1991 09:00"}
