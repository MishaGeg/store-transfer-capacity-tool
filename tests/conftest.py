import os
from dotenv import load_dotenv
from models import User, db

load_dotenv()
real_url = os.environ["DATABASE_URL"]
os.environ["DATABASE_URL"] = real_url.rsplit("/", 1)[0] + "/store_transfer_test"

import pytest

from app import app
from models import db


@pytest.fixture
def client():
    with app.app_context():
        assert app.config["SQLALCHEMY_DATABASE_URI"].endswith("store_transfer_test")
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

@pytest.fixture
def logged_in_client(client):
    user = User(username="testuser")
    user.set_password("secret123")
    db.session.add(user)
    db.session.commit()
    response = client.post("/login", json={"username" : "testuser", "password" : "secret123"}) 
    assert response.status_code == 200
    return client
