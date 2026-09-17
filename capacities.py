from flask import Blueprint, request, jsonify
from models import BrandCapacity, db, Store, PlannedTransfer, StockSnapshot
from datetime import datetime, timedelta
from sqlalchemy import func

capacities_bp = Blueprint("capacities", __name__)

@capacities_bp.route("/capacities", methods=["GET"])
def show_capacities():
    result = db.session.query(BrandCapacity, Store).join(Store, BrandCapacity.store_id == Store.id).all()
    results = {}
    for capacity, store in result:
        store_name = store.name
        if store_name not in results:
            results[store_name] = {"store_id": store.id,"brands": []}
        results[store_name]["brands"].append({"brand": capacity.brand,"capacity": capacity.capacity})
    return jsonify(results)          

@capacities_bp.route("/capacities/<int:store_id>/<brand>", methods =["PUT"])
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

@capacities_bp.route("/capacity-check", methods=["GET"])
def check_capacity():
    result = db.session.query(BrandCapacity, Store).join(Store, BrandCapacity.store_id == Store.id).all()
    free_space = {}
    for c in result:
        current_transfers = 0
        store_id = c[1].id
        name = c[1].name
        capacity = c[0].capacity
        brand = c[0].brand

        for t in PlannedTransfer.query.filter(
            PlannedTransfer.submitted_at > datetime.now() - timedelta(days=5),
            PlannedTransfer.to_store_id == store_id
        ).all():
            current_transfers += t.quantity       

        current_stock_row = StockSnapshot.query.filter(
            StockSnapshot.store_id == store_id, StockSnapshot.brand == brand, StockSnapshot.category == "FOOTWEAR"
        ).first()
        if current_stock_row:
            current_stock = current_stock_row.quantity
        else:
            current_stock = 0

        if name not in free_space:
            free_space[name] = {}
        free_space[name][brand] = capacity - current_stock - current_transfers
    return jsonify(free_space)        


        
            


    


