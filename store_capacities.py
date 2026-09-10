from flask import Blueprint, request, jsonify
from models import BrandCapacity, db, Store

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