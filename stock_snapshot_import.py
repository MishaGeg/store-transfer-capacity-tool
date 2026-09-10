from models import StockSnapshot, db
from datetime import datetime
from openpyxl import load_workbook
from models import  Store
from flask import Blueprint, request, render_template, jsonify


CAT_1_COL = 0
BRAND_1_COL = 3
ST_COL = 4
QTY_COL = 5

snapshot_import_bp = Blueprint("snapshot", __name__)

@snapshot_import_bp.route("/import-stock", methods=["GET", "POST"])
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

def read_stock_data(file):
    if not file or not file.filename.endswith(".xlsx"):
        raise ValueError("Please upload a .xlsx file")
    workbook = load_workbook(file, data_only=True)
    sheet = workbook.active
    store_lookup = {store.name: store.id for store in Store.query.all()}
    return(sheet, store_lookup)
       
def validate_stock_data(sheet, store_lookup):
    processed = 0
    skipped = []
    totals = {}
    for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        category = row[CAT_1_COL]
        brand = row[BRAND_1_COL]
        st_name = row[ST_COL]
        quantity = row[QTY_COL]
        if category is None or str(category).strip().upper() not in {"FOOTWEAR", "SLIPPERS"}:
            continue
        if quantity is None or str(quantity).strip() == "":
            skipped.append({"row": row_num, "reason": "empty quantity"})
            continue
        store_id = store_lookup.get(str(st_name).strip() if st_name else None)
        if store_id is None:
            skipped.append({"row": row_num, "reason": f"unknown ST value: {st_name}"})
            continue
        if brand is None or str(brand).strip() == "":
            skipped.append({"row": row_num, "reason": "empty brand"})
            continue
        try:
            key = (store_id, str(brand).strip(), str(category).strip().upper())
            totals[key] = totals.get(key, 0) + int(quantity)
        except (TypeError, ValueError):
            skipped.append({"row": row_num, "reason": "quantity number error"})
            continue
        processed += 1
    return(processed, skipped, totals)

def update_stock_data(store_id, brand, category, quantity):
    stock_snapshot = StockSnapshot.query.filter_by(store_id=store_id, brand=brand, category=category).first()
    if stock_snapshot:
        stock_snapshot.quantity = quantity
        stock_snapshot.snapshot_date = datetime.now()
    else:
        new_stock_snapshot = StockSnapshot(
            store_id=store_id, brand=brand, 
            category=category, 
            quantity=quantity, 
            snapshot_date=datetime.now()
 )
        db.session.add(new_stock_snapshot)

def write_stock_data(totals):
    for k, v in totals.items():
        store_id = k[0]
        brand = k[1]
        category = k[2]
        quantity = v
        update_stock_data(store_id, brand, category, quantity)
    db.session.commit()        