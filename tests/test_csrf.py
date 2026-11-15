from io import BytesIO
import re
import time

from openpyxl import Workbook
import pytest

from models import BrandCapacity, PlannedTransfer, StockSnapshot, Store, User, db


def send(client, method, path, **kwargs):

    with client.application.app_context():
        return client.open(path, method=method, **kwargs)


def page_token(client, path="/login"):
    response = send(client, "GET", path)
    assert response.status_code == 200
    return re.search(
        r'<meta name="csrf-token" content="([^"]+)">',
        response.get_data(as_text=True),
    ).group(1)


@pytest.fixture
def csrf_client(client, monkeypatch):
    monkeypatch.setitem(client.application.config, "WTF_CSRF_ENABLED", True)
    user = User(username="csrf_user", role="supply_chain")
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()
    return client


def login(client):
    token = page_token(client)
    response = send(
        client, "POST", "/login",
        headers={"X-CSRFToken": token},
        json={"username": "csrf_user", "password": "test-password"},
    )
    assert response.status_code == 200
    return token


@pytest.mark.parametrize("method,path", [
    ("POST", "/login"),
    ("POST", "/logout"),
    ("POST", "/transfers"),
    ("DELETE", "/transfers/1"),
    ("PUT", "/capacities/1/ECCOGEOXSTUDIO"),
    ("POST", "/import-stock"),
])
@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_changes_reject_missing_or_invalid_tokens(csrf_client, method, path, token):
    login(csrf_client)
    headers = {"X-CSRFToken": token} if token else {}
    response = send(csrf_client, method, path, headers=headers, json={})
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Security check failed. Reload the page and try again."
    }
    assert PlannedTransfer.query.count() == 0
    assert BrandCapacity.query.count() == 0
    assert StockSnapshot.query.count() == 0

    assert send(csrf_client, "GET", "/stores").status_code == 200


@pytest.mark.parametrize("path", [
    "/transfers-page", "/edit-capacities", "/import-stock", "/public-transfers",
])
def test_management_pages_supply_valid_tokens(csrf_client, path):
    login(csrf_client)
    token = page_token(csrf_client, path)
    assert send(
        csrf_client, "POST", "/logout", headers={"X-CSRFToken": token},
    ).status_code == 200
    assert send(csrf_client, "GET", "/stores").status_code == 401


def test_store_manager_view_supplies_valid_logout_token(csrf_client):
    user = User.query.filter_by(username="csrf_user").one()
    user.role = "store_manager"
    db.session.commit()
    login(csrf_client)
    token = page_token(csrf_client, "/public-transfers")
    assert send(
        csrf_client, "POST", "/logout", headers={"X-CSRFToken": token},
    ).status_code == 200


def test_token_from_another_session_is_rejected(csrf_client):
    login(csrf_client)
    other_client = csrf_client.application.test_client()
    other_token = page_token(other_client)
    response = send(
        csrf_client, "POST", "/logout", headers={"X-CSRFToken": other_token},
    )
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Security check failed. Reload the page and try again."
    }
    assert send(csrf_client, "GET", "/stores").status_code == 200


def test_expired_token_is_rejected(csrf_client, monkeypatch):
    token = login(csrf_client)
    later = time.time() + csrf_client.application.config.get("WTF_CSRF_TIME_LIMIT", 3600) + 1
    monkeypatch.setattr(time, "time", lambda: later)
    response = send(
        csrf_client, "POST", "/logout", headers={"X-CSRFToken": token},
    )
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Security check failed. Reload the page and try again."
    }


def test_valid_tokens_allow_upload_capacity_transfer_and_deletion(csrf_client):
    login(csrf_client)
    source = Store(name="CSRF source", type="store")
    destination = Store(name="CSRF destination", type="store")
    db.session.add_all([source, destination])
    db.session.commit()

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Category", "", "", "Brand", "Store", "Segment", "Quantity"])
    sheet.append(["FOOTWEAR", "", "", "ECCO", source.name, "ADULTS", 10])
    upload = BytesIO()
    workbook.save(upload)
    upload.seek(0)
    response = send(
        csrf_client, "POST", "/import-stock",
        headers={"X-CSRFToken": page_token(csrf_client, "/import-stock")},
        data={"file": (upload, "stock.xlsx")},
    )
    assert response.status_code == 200
    assert StockSnapshot.query.one().quantity == 10

    response = send(
        csrf_client, "PUT", f"/capacities/{destination.id}/ECCOGEOXSTUDIO",
        headers={"X-CSRFToken": page_token(csrf_client, "/edit-capacities")},
        json={"capacity": 100},
    )
    assert response.status_code == 200
    assert BrandCapacity.query.one().capacity == 100

    token = page_token(csrf_client, "/transfers-page")
    response = send(
        csrf_client, "POST", "/transfers", headers={"X-CSRFToken": token},
        json={"transfers": [{
            "from_store_id": source.id, "to_store_id": destination.id,
            "brand": "ECCO", "segment": "ADULTS", "quantity": 2,
        }]},
    )
    assert response.status_code == 201
    transfer = PlannedTransfer.query.one()
    assert transfer.quantity == 2
    assert send(
        csrf_client, "DELETE", f"/transfers/{transfer.id}",
        headers={"X-CSRFToken": token},
    ).status_code == 200
    assert PlannedTransfer.query.count() == 0
