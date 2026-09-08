from flask import Flask, request, render_template, redirect, flash, url_for, session
from dotenv import load_dotenv
import os
from models import db, Store, BrandCapacity, PlannedTransfer
from flask_migrate import Migrate
from snapshot_import import  write_stock_data
from flask import request, jsonify
from snapshot_reader import read_stock_data, validate_stock_data
from flask_cors import CORS
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
CORS(app)

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

@app.route("/capacities", methods=["GET"])
def show_capacities():
    result = db.session.query(BrandCapacity, Store).join(Store, BrandCapacity.store_id == Store.id).all()
    results = {}
    for capacity, store in result:
        store_name = store.name
        if store_name not in results:
            results[store_name] = {"store_id": store.id,"brands": []}
        results[store_name]["brands"].append({"brand": capacity.brand,"capacity": capacity.capacity})
    return jsonify(results)          

@app.route("/capacities/<int:store_id>/<brand>", methods =["PUT"])
def update_capacities(store_id, brand):
    result = BrandCapacity.query.filter_by(store_id = store_id, brand = brand).first()
    if not result:
        return jsonify({"error": "wrong store/brand name"}), 404
    data = request.get_json()
    try:
        new_capacity = int(data["capacity"])
    except(TypeError, ValueError):
        return jsonify({"error": "incorrect data"}), 400  
    result.capacity = new_capacity
    db.session.commit()
    return jsonify({"brand": result.brand, "capacity": result.capacity}), 200

@app.route("/transfers", methods =["POST"])
def create_transfers():
    data = request.get_json()
    transfers = data.get("transfers")
    if not isinstance(transfers, list):
        return jsonify({"error": "transfers must be a list"}), 400
    for transfer in transfers:
        try:
            brand = transfer["brand"]
            from_store_id = transfer["from_store_id"]
            to_store_id = transfer["to_store_id"]
            quantity = transfer["quantity"]
        except(KeyError):
            return jsonify({"error": f"incorrect{transfer}data"})    



    

if __name__ == "__main__":
    app.run(debug=True)