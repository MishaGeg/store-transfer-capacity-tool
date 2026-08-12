from flask import Flask, request, render_template, redirect, flash, url_for, session
from dotenv import load_dotenv
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import text

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(20), nullable=False)

    __table_args__ = (
        db.CheckConstraint("type IN ('store', 'warehouse')", name="check_store_type"),
    )



@app.route("/")
def home():
    try:
        db.session.execute(text("SELECT 1"))
        return "Store Transfer Capacity Visibility Tool is running. Database: connected"
    except Exception:
        return "Store Transfer Capacity Visibility Tool is running. Database: unreachable", 500



   
if __name__ == "__main__":
    app.run(debug=True)