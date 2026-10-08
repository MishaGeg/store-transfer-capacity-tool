from models import db, User

def test_login_success(client):
    user = User(username="testuser")
    user.set_password("test123")
    db.session.add(user)
    db.session.commit()
    response = client.post("/login", json={"username" : "testuser", "password" : "test123"})
    assert response.status_code == 200
    response.get_json()["message"] == "Login successful"

def test_login_wrong_password(client):
    user = User(username="testuser")
    user.set_password("test123")
    db.session.add(user)
    db.session.commit()
    response = client.post("/login", json={"username" : "testuser", "password" : "test12"})
    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid username or password"

def test_login_unknown_user(client):
    response = client.post("/login", json={"username" : "testuser", "password" : "test123"})
    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid username or password"

def test_create_transfer_requires_login(client):
    response = client.post("/transfers", json=[])
    assert response.status_code == 401