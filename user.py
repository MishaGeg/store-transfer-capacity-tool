from flask import Blueprint, request, jsonify
from models import User, db
from flask_login import login_user


auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    user = db.session.execute(
        db.select(User).where(User.username == username)
    ).scalar_one_or_none()

    if user is None or not user.check_password(password):
        return {"error": "Invalid username or password"}, 401
    
    login_user(user)

    return {"message": "Login successful"}, 200
