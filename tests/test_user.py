from models import User


def test_correct_password():
    user = User(username="testuser", role="supply_chain")

    user.set_password("secret123")

    assert user.check_password("secret123") is True


def test_wrong_password():
    user = User(username="testuser", role="supply_chain")

    user.set_password("secret123")

    assert user.check_password("wrongpassword") is False

def test_password_is_hashed():

    user = User(username="testuser", role="supply_chain")
    user.set_password("secret123")

    assert user.password_hash != "secret123"  