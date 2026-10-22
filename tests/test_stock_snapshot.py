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
        ("FOOTWEAR", None, None, "ECCO", "Main", "ADULTS", 2),
        ("FOOTWEAR", None, None, "ECCO", "Main", "ADULTS", "3"),
        ("SLIPPERS", None, None, "GEOX", "Missing", "ADULTS", 1),
        ("FOOTWEAR", None, None, "ECCO", "Main", "KIDS", 8),
        ("FOOTWEAR", None, None, "ECCO", "Main", "ADULTS", "bad"),
    ])

    processed, skipped, totals = validate_stock_data(sheet, {"Main": 7})

    assert processed == 2
    assert totals == {(7, "ECCO", "FOOTWEAR"): 5}
    assert skipped == [
        {"row": 4, "reason": "არასწორი მაღაზია: Missing"},
        {"row": 6, "reason": "არასწორი რაოდენობა"},
    ]


def test_write_stock_data_creates_then_replaces_snapshot_quantity(client):
    store = Store(name="Main", type="store")
    db.session.add(store)
    db.session.commit()

    key = (store.id, "ECCO", "FOOTWEAR")
    write_stock_data({key: 10})
    first_updated_at = StockSnapshot.query.one().snapshot_date
    write_stock_data({key: 15})

    snapshot = StockSnapshot.query.one()
    assert snapshot.quantity == 15
    assert snapshot.snapshot_date >= first_updated_at


def test_stock_read_apis_return_current_data_and_latest_timestamp(logged_in_client):
    store = Store(name="Main", type="store")
    db.session.add(store)
    db.session.commit()
    snapshot = StockSnapshot(
        store_id=store.id, brand="ECCO", category="FOOTWEAR", quantity=9,
        snapshot_date=datetime(2026, 1, 2, 14, 30),
    )
    db.session.add(snapshot)
    db.session.commit()

    assert logged_in_client.get("/current-stock").get_json() == [{
        "store_id": store.id, "store_name": "Main", "brand": "ECCO",
        "category": "FOOTWEAR", "quantity": 9,
    }]
    assert logged_in_client.get("/last-stock-update").get_json() == {"last_updated": "02.01.2026 14:30"}
