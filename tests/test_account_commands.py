import click
import pytest
from sqlalchemy.exc import SQLAlchemyError

from models import User, db


@pytest.fixture(autouse=True)
def masked_password_input(monkeypatch):
    # CliRunner has no real terminal; use its hidden-input support for getpass.
    def read_password(prompt, *, echo_char):
        assert echo_char == "*"
        return click.prompt(prompt.rstrip(": "), hide_input=True, default="", show_default=False)

    monkeypatch.setattr("user.getpass", read_password)


@pytest.mark.parametrize("role", ["supply_chain", "store_manager"])
def test_create_user_with_prompted_password(client, role):
    result = client.application.test_cli_runner().invoke(
        args=["auth", "create-user", " anna ", "--role", role],
        input="new-password\nnew-password\n",
    )
    assert result.exit_code == 0
    assert "Created user: anna" in result.output
    assert "new-password" not in result.output
    user = User.query.filter_by(username="anna").one()
    assert user.role == role
    assert user.check_password("new-password")
    assert user.password_hash != "new-password"


@pytest.mark.parametrize("arguments,password_input", [
    (["anna", "--role", "admin"], ""),
    (["anna"], ""),
    (["   ", "--role", "store_manager"], "password\npassword\n"),
    (["a" * 121, "--role", "store_manager"], "password\npassword\n"),
    (["anna", "--role", "store_manager"], "first\nsecond\n"),
    (["anna", "--role", "store_manager"], "\n\n"),
])
def test_invalid_creation_does_not_create_account(client, arguments, password_input):
    result = client.application.test_cli_runner().invoke(
        args=["auth", "create-user", *arguments], input=password_input,
    )
    assert result.exit_code != 0
    assert User.query.count() == 0


@pytest.mark.parametrize("command", ["create-user", "reset-password"])
def test_existing_account_changes_only_on_password_reset(client, command):
    user = User(username="anna", role="store_manager")
    user.set_password("old-password")
    db.session.add(user)
    db.session.commit()
    arguments = ["auth", command, "anna"]
    if command == "create-user":
        arguments += ["--role", "supply_chain"]

    result = client.application.test_cli_runner().invoke(
        args=arguments, input="new-password\nnew-password\n",
    )
    db.session.expire_all()
    saved = User.query.filter_by(username="anna").one()
    assert saved.role == "store_manager"
    assert "new-password" not in result.output
    if command == "reset-password":
        assert result.exit_code == 0
        assert "Updated password for: anna" in result.output
        assert saved.check_password("new-password")
        assert not saved.check_password("old-password")
    else:
        assert result.exit_code != 0
        assert "Username already exists." in result.output
        assert saved.check_password("old-password")
        assert not saved.check_password("new-password")


def test_reset_unknown_account_does_not_create_it(client):
    result = client.application.test_cli_runner().invoke(
        args=["auth", "reset-password", "missing"],
        input="new-password\nnew-password\n",
    )
    assert result.exit_code != 0
    assert "Username does not exist." in result.output
    assert User.query.count() == 0


@pytest.mark.parametrize("password_input", ["\n\n", "first\nsecond\n"])
def test_invalid_password_reset_preserves_password(client, password_input):
    user = User(username="anna", role="supply_chain")
    user.set_password("old-password")
    db.session.add(user)
    db.session.commit()
    result = client.application.test_cli_runner().invoke(
        args=["auth", "reset-password", "anna"], input=password_input,
    )
    assert result.exit_code != 0
    db.session.expire_all()
    assert User.query.filter_by(username="anna").one().check_password("old-password")


@pytest.mark.parametrize("command", ["create-user", "reset-password"])
def test_failed_commit_rolls_back_account_command(client, monkeypatch, command):
    if command == "reset-password":
        user = User(username="anna", role="store_manager")
        user.set_password("old-password")
        db.session.add(user)
        db.session.commit()

    def fail_commit():
        raise SQLAlchemyError("database unavailable")

    arguments = ["auth", command, "anna"]
    if command == "create-user":
        arguments += ["--role", "store_manager"]
    with monkeypatch.context() as patch:
        patch.setattr(db.session, "commit", fail_commit)
        result = client.application.test_cli_runner().invoke(
            args=arguments, input="new-password\nnew-password\n",
        )

    assert result.exit_code != 0
    assert "Could not" in result.output
    assert "Created user:" not in result.output
    assert "Updated password for:" not in result.output
    assert "database unavailable" not in result.output
    if command == "create-user":
        assert User.query.count() == 0
    else:
        assert User.query.filter_by(username="anna").one().check_password("old-password")
