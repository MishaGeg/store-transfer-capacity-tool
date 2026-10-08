from app import app


def test_home():
    client = app.test_client()  

    response = client.get("/")

    assert response.status_code == 200
    assert response.data == b"HI"

def test_app_uses_test_database():
    assert app.config["SQLALCHEMY_DATABASE_URI"].endswith("store_transfer_test")    