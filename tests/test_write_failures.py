from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
import pytest
from sqlalchemy.exc import SQLAlchemyError

from models import PlannedTransfer, StockSnapshot, Store, db
import stock_snapshot


def fail_commit():
    db.session.flush()
    raise SQLAlchemyError("private database details")


@pytest.fixture
def stores(logged_in_client):
    source = Store(name="Failure test source", type="store")
    destination = Store(name="Failure test destination", type="warehouse")
    db.session.add_all([source, destination])
    db.session.commit()
    return source, destination


@pytest.mark.parametrize("mixed", [False, True])
def test_failed_transfer_batch_rolls_back_all_rows(logged_in_client, stores, monkeypatch, mixed, caplog):
    source, destination = stores
    rows = [{
        "brand": brand, "segment": "ADULTS", "quantity": 2,
        "from_store_id": source.id, "to_store_id": destination.id,
    } for brand in ("ECCO", "GEOX")]
    if mixed:
        rows.append({"brand": "ECCO"})

    with monkeypatch.context() as patch:
        patch.setattr(db.session, "commit", fail_commit)
        response = logged_in_client.post("/transfers", json={"transfers": rows})

    assert response.status_code == 500
    assert response.get_json() == {"error": "Could not save transfers. Please try again."}
    records = [record for record in caplog.records if record.getMessage() == "Could not save transfers"]
    assert len(records) == 1
    assert records[0].exc_info is not None
    assert PlannedTransfer.query.count() == 0

    retry = logged_in_client.post("/transfers", json={"transfers": rows})
    assert retry.status_code == (207 if mixed else 201)
    assert PlannedTransfer.query.count() == 2


def test_failed_transfer_deletion_preserves_row_and_allows_retry(logged_in_client, stores, monkeypatch, caplog):
    source, destination = stores
    transfer = PlannedTransfer(
        brand="ECCO", segment="ADULTS", quantity=2,
        from_store_id=source.id, to_store_id=destination.id,
    )
    db.session.add(transfer)
    db.session.commit()
    transfer_id = transfer.id

    with monkeypatch.context() as patch:
        patch.setattr(db.session, "commit", fail_commit)
        response = logged_in_client.delete(f"/transfers/{transfer_id}")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Could not delete transfer. Please try again."}
    records = [record for record in caplog.records if record.getMessage() == "Could not delete transfer"]
    assert len(records) == 1
    assert records[0].exc_info is not None
    assert PlannedTransfer.query.one().id == transfer_id

    assert logged_in_client.delete(f"/transfers/{transfer_id}").status_code == 200
    assert PlannedTransfer.query.count() == 0


def stock_upload(store_name):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Category", "", "", "Brand", "Store", "Segment", "Quantity"])
    for brand, quantity in (("ECCO", 100), ("GEOX", 5)):
        sheet.append(["FOOTWEAR", "", "", brand, store_name, "ADULTS", quantity])
    upload = BytesIO()
    workbook.save(upload)
    upload.seek(0)
    return {"file": (upload, "stock.xlsx")}


@pytest.mark.parametrize("failure_stage", ["commit", "upsert"])
def test_failed_stock_import_rolls_back_updates_and_inserts(
    logged_in_client, stores, monkeypatch, failure_stage, caplog,
):
    source, _ = stores
    store_name = source.name
    original_date = datetime(2026, 1, 1)
    db.session.add(StockSnapshot(
        store_id=source.id, brand="ECCO", category="FOOTWEAR",
        segment="ADULTS", quantity=10, snapshot_date=original_date,
    ))
    db.session.commit()
    original_update = stock_snapshot.update_stock_data
    updates = []

    def fail_upsert(*args):
        original_update(*args)
        db.session.flush()
        updates.append(args)
        if len(updates) == 2:
            raise SQLAlchemyError("private database details")

    with monkeypatch.context() as patch:
        if failure_stage == "commit":
            patch.setattr(db.session, "commit", fail_commit)
        else:
            patch.setattr(stock_snapshot, "update_stock_data", fail_upsert)
        response = logged_in_client.post("/import-stock", data=stock_upload(store_name))

    assert response.status_code == 500
    assert response.get_json() == {"error": "Could not save stock. Please try again."}
    records = [record for record in caplog.records if record.getMessage() == "Could not save stock"]
    assert len(records) == 1
    assert records[0].exc_info is not None
    snapshot = StockSnapshot.query.one()
    assert snapshot.brand == "ECCO"
    assert snapshot.quantity == 10
    assert snapshot.snapshot_date == original_date

    retry = logged_in_client.post("/import-stock", data=stock_upload(store_name))
    assert retry.status_code == 200
    assert retry.get_json() == {"processed": 2, "skipped": []}
    assert {(row.brand, row.quantity) for row in StockSnapshot.query.all()} == {
        ("ECCO", 100), ("GEOX", 5),
    }
