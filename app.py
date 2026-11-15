from flask import Flask, jsonify, redirect, request
from dotenv import load_dotenv
import os
from models import db, User
from flask_migrate import Migrate
from transfers import transfers_bp
from capacities import capacities_bp
from stock_snapshot import stock_snapshot_bp
from stores import stores_bp
from user import auth_bp
from flask_login import LoginManager
from datetime import timedelta
from flask_wtf.csrf import CSRFProtect, CSRFError
from extensions import limiter
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("APP_ENV") == "production"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=5)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

csrf = CSRFProtect(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)

db.init_app(app)
limiter.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    """Restore the logged-in user from the ID stored in the session."""
    return db.session.get(User, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():

    if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "text/html":
        return redirect("/login")
    return jsonify({"error": "გთხოვთ შეხვიდეთ სისტემაში"}), 401

@app.errorhandler(413)
def too_large(error):
    return jsonify({"error": "ფაილის ზომა აჭარბებს ლიმიტს"}), 413

@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    return {
        "error": "Security check failed. Reload the page and try again."
    }, 400

@app.errorhandler(429)
def too_many_requests(error):
    return {
        "error": "Too many login attempts. Please wait a minute and try again."
    }, 429

app.register_blueprint(transfers_bp)
app.register_blueprint(capacities_bp)
app.register_blueprint(stock_snapshot_bp)
app.register_blueprint(stores_bp)
app.register_blueprint(auth_bp)


@app.route("/")
def home():
    return redirect("/login")


if __name__ == "__main__":
    app.run()
