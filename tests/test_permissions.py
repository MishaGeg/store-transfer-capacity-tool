import pytest

from models import BrandCapacity, PlannedTransfer, StockSnapshot, User, db


MANAGEMENT_REQUESTS = [
    ("GET", "/transfers-page"),
    ("GET", "/transfer-options?brand=ECCO&segment=ADULTS"),
    ("GET", "/transfers"),
    ("POST", "/transfers"),
    ("DELETE", "/transfers/1"),
    ("GET", "/edit-capacities"),
    ("GET", "/capacities"),
    ("PUT", "/capacities/1/ECCOGEOXSTUDIO"),
    ("GET", "/import-stock"),
    ("POST", "/import-stock"),
    ("GET", "/current-stock"),
    ("GET", "/last-stock-update"),
    ("GET", "/stores"),
]


@pytest.mark.parametrize("method,path", MANAGEMENT_REQUESTS)
def test_anonymous_cannot_access_management(client, method, path):
    response = client.open(path, method=method)
    assert response.status_code == 401


@pytest.mark.parametrize("method,path", MANAGEMENT_REQUESTS)
def test_store_manager_cannot_access_management(client, method, path):
    user = User(username="manager", role="store_manager")
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()
    assert client.post("/login", json={
        "username": "manager", "password": "test-password",
    }).status_code == 200

    response = client.open(path, method=method)
    assert response.status_code == 403
    assert PlannedTransfer.query.count() == 0
    assert StockSnapshot.query.count() == 0
    assert BrandCapacity.query.count() == 0


@pytest.mark.parametrize("path", ["/public-transfers", "/view-transfers"])
def test_anonymous_cannot_view_transfers(client, path):
    assert client.get(path).status_code == 401
    response = client.get(path, headers={"Accept": "text/html"})
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


@pytest.mark.parametrize("role,next_page", [
    ("supply_chain", "/transfers-page"),
    ("store_manager", "/public-transfers"),
])
def test_roles_can_view_transfers_and_receive_login_destination(client, role, next_page):
    user = User(username="viewer", role=role)
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()

    response = client.post("/login", json={
        "username": "viewer", "password": "test-password",
    })
    assert response.status_code == 200
    assert response.get_json()["next_page"] == next_page
    assert client.get(next_page).status_code == 200
    assert client.get("/public-transfers").status_code == 200
    assert client.get("/view-transfers").status_code == 200

    assert client.post("/logout").status_code == 200
    assert client.get("/view-transfers").status_code == 401


@pytest.mark.parametrize("role", ["supply_chain", "store_manager"])
def test_viewing_page_navigation_matches_role(client, role):
    user = User(username="viewer", role=role)
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()
    assert client.post("/login", json={
        "username": "viewer", "password": "test-password",
    }).status_code == 200

    response = client.get("/public-transfers")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count('id="logoutBtn"') == 1
    assert '<h2>ტრანსფერები</h2>' in html

    for path in ("/import-stock", "/transfers-page", "/edit-capacities"):
        assert (f'href="{path}"' in html) == (role == "supply_chain")

    if role == "supply_chain":
        assert '<nav class="nav">' in html
        assert 'href="/public-transfers" class="action-btn current" aria-current="page"' in html
        assert html.index('id="logoutBtn"') < html.index('<h2>')
    else:
        assert '<nav class="nav">' not in html
        assert html.index('<h2>') < html.index('id="logoutBtn"')
