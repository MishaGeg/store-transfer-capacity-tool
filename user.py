from flask import Blueprint, request, render_template
from models import User, db
from flask_login import login_user, logout_user


auth_bp = Blueprint("auth", __name__)

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

    return {"message": "Login successful"}, 200

@auth_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return {"message": "Logout successful"}, 200
