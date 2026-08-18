from openpyxl import load_workbook
from models import  Store


CAT_1_COL = 0
BRAND_1_COL = 3
ST_COL = 4
QTY_COL = 5

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
        try:
            key = (store_id, str(brand).strip(), str(category).strip().upper())
            totals[key] = totals.get(key, 0) + int(quantity)
        except (TypeError, ValueError):
            skipped.append({"row": row_num, "reason": "quantity number error"})
            continue
        processed += 1
    return(processed, skipped, totals)

