from flask import Flask, request, render_template, redirect, flash, url_for, session
from dotenv import load_dotenv
import os
from models import db, Store, StockSnapshot
from flask_migrate import Migrate
from snapshot_import import update_stock_data
from flask import request, jsonify
from openpyxl import load_workbook

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

db.init_app(app)
migrate = Migrate(app, db)

@app.route("/")
def home():
    return "HI"

CAT_1_COL = 0
BRAND_1_COL = 3
ST_COL = 4
QTY_COL = 5

@app.route("/import-stock", methods=["GET", "POST"])
def import_stock():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename.endswith(".xlsx"):
            return jsonify({"error": "Please upload a .xlsx file"}), 400
        workbook = load_workbook(file, data_only=True)
        sheet = workbook.active
        store_lookup = {store.name: store.id for store in Store.query.all()}
        processed = 0
        skipped = []
        totals = {}
        for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            category = row[CAT_1_COL]
            brand = row[BRAND_1_COL]
            st_value = row[ST_COL]
            quantity = row[QTY_COL]
            if category is None or str(category).strip().upper() not in {"FOOTWEAR", "SLIPPERS"}:
                continue
            if quantity is None or str(quantity).strip() == "":
                skipped.append({"row": row_num, "reason": "empty quantity"})
                continue
            store_id = store_lookup.get(str(st_value).strip() if st_value else None)
            if store_id is None:
                skipped.append({"row": row_num, "reason": f"unknown ST value: {st_value}"})
                continue
            if brand is None or str(brand).strip() == "":
                skipped.append({"row": row_num, "reason": "empty brand"})
                continue
            key = (store_id, str(brand).strip(), str(category).strip().upper())
            totals[key] = totals.get(key, 0) + int(quantity)
            processed += 1
        for k, v in totals.items():
                store_id = k[0]
                brand = k[1]
                category = k[2]
                quantity = v
                update_stock_data(store_id, brand, category, quantity)
        db.session.commit()
        return jsonify({"processed": processed, "skipped": skipped})      
    else:        
        return render_template("import.html")

   
if __name__ == "__main__":
    app.run(debug=True)