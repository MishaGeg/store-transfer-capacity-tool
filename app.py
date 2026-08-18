from flask import Flask, request, render_template, redirect, flash, url_for, session
from dotenv import load_dotenv
import os
from models import db
from flask_migrate import Migrate
from snapshot_import import  write_stock_data
from flask import request, jsonify
from snapshot_reader import read_stock_data, validate_stock_data
load_dotenv()


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

db.init_app(app)
migrate = Migrate(app, db)

@app.route("/")
def home():
    return "HI"

@app.route("/import-stock", methods=["GET", "POST"])
def import_stock():
    if request.method == "POST":
        file = request.files.get("file")
        try:
            sheet, store_lookup = read_stock_data(file)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        processed, skipped, totals = validate_stock_data(sheet, store_lookup)
        write_stock_data(totals)
        return jsonify({"processed": processed, "skipped": skipped})
    return render_template("import.html")

if __name__ == "__main__":
    app.run(debug=True)