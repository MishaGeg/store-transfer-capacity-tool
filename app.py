from flask import Flask, jsonify, redirect, request
from dotenv import load_dotenv
import os
from models import db, User
from flask_migrate import Migrate
from flask_cors import CORS
from transfers import transfers_bp
from capacities import capacities_bp
from stock_snapshot import stock_snapshot_bp
from stores import stores_bp
from user import auth_bp
from flask_login import LoginManager
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
db.init_app(app)
migrate = Migrate(app, db)
CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "text/html":
        return redirect("/login")
    return jsonify({"error": "გთხოვთ შეხვიდეთ სისტემაში"}), 401

@app.errorhandler(413)
def too_large(error):
    return jsonify({"error": "ფაილის ზომა აჭარბებს ლიმიტს"}), 413

app.register_blueprint(transfers_bp)
app.register_blueprint(capacities_bp)
app.register_blueprint(stock_snapshot_bp)
app.register_blueprint(stores_bp)
app.register_blueprint(auth_bp)


@app.route("/")
def home():
    return "HI"


if __name__ == "__main__":
    app.run(debug=True)