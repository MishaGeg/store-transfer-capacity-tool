from flask import Flask, request, render_template, redirect, flash, url_for, session
from dotenv import load_dotenv
import os
from models import db, Store, StockSnapshot
from flask_migrate import Migrate
from snapshot_import import update_stock_data

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

db.init_app(app)
migrate = Migrate(app, db)




@app.route("/")
def home():
    return "HI"

@app.route("/test-upsert")
def test_upsert():
    update_stock_data(store_id=1, brand="Nike", category="footwear", quantity=500)
    return "done"



   
if __name__ == "__main__":
    app.run(debug=True)