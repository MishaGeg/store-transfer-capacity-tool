from app import app


def test_home_redirects_to_login():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"

def test_app_uses_test_database():
    assert app.config["SQLALCHEMY_DATABASE_URI"].endswith("store_transfer_test")
