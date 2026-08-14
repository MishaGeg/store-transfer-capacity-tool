from models import StockSnapshot, db
from datetime import datetime

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
    db.session.commit()