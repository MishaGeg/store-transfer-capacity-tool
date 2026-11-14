from flask import Blueprint, request, render_template
from models import User, db
from flask_login import login_user, logout_user
import click
from getpass import getpass
from sqlalchemy.exc import SQLAlchemyError

auth_bp = Blueprint("auth", __name__)


def prompt_password():
    """Read and confirm a password, displaying asterisks while typing."""
    password = getpass("Password: ", echo_char="*")
    if not password:
        raise click.ClickException("Password cannot be empty.")

    confirmation = getpass("Repeat for confirmation: ", echo_char="*")
    if password != confirmation:
        raise click.ClickException("Passwords do not match.")

    return password


@auth_bp.cli.command("create-user")
@click.argument("username")
@click.option(
    "--role",
    required=True,
    type=click.Choice(["supply_chain", "store_manager"]),
)
def create_user(username, role):
    """Create a new account without changing existing users."""
    username = username.strip()

    if not username or len(username) > 120:
        raise click.ClickException("Username must contain 1–120 characters.")

    existing_user = User.query.filter_by(username=username).first()

    if existing_user:
        raise click.ClickException("Username already exists.")

    password = prompt_password()
    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise click.ClickException("Could not save the account.") from None

    click.echo(f"Created user: {username}, role: {role}")


@auth_bp.cli.command("reset-password")
@click.argument("username")
def reset_password(username):
    """Reset an existing user's password without changing their role."""
    user = User.query.filter_by(username=username.strip()).first()

    if user is None:
        raise click.ClickException("Username does not exist.")

    password = prompt_password()
    user.set_password(password)

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise click.ClickException("Could not reset the password.") from None

    click.echo(f"Updated password for: {user.username}")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return {"error": "Username and password are required"}, 400

    user = db.session.execute(
        db.select(User).where(User.username == username)
    ).scalar_one_or_none()

    # Use the same error for both cases to avoid revealing which usernames exist.
    if user is None or not user.check_password(password):
        return {"error": "Invalid username or password"}, 401

    login_user(user)

    if user.role == "supply_chain":
        next_page = "/transfers-page"
    else:
        next_page = "/public-transfers"

    return {"message": "Login successful", "next_page": next_page}, 200


@auth_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return {"message": "Logout successful"}, 200
