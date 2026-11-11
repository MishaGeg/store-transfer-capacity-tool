from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from catalog import pool_labels
from models import BrandCapacity, Store, db


capacities_bp = Blueprint("capacities", __name__)


def capacity_list():
    values = {
        (row.store_id, row.brand): row.capacity
        for row in BrandCapacity.query.all()
    }
    pools = pool_labels()
    return [
        {
            "store_id": store.id,
            "store_name": store.name,
            "capacities": {
                pool: values.get((store.id, pool))
                for pool in pools
            },
        }
        for store in Store.query.order_by(Store.name).all()
    ]


@capacities_bp.route("/edit-capacities")
@login_required
def edit_capacities():
    return render_template("edit-capacities.html")


@capacities_bp.route("/capacities", methods=["GET"])
@login_required
def show_capacities():
    return jsonify(capacity_list())


@capacities_bp.route("/capacities/<int:store_id>/<brand>", methods=["PUT"])
@login_required
def update_capacities(store_id, brand):
    if brand not in pool_labels() or db.session.get(Store, store_id) is None:
        return jsonify({"error": "wrong store/brand name"}), 404

    data = request.get_json(silent=True) or {}
    try:
        new_capacity = int(data.get("capacity"))
        if new_capacity < 0:
            return jsonify({"error": "capacity cannot be negative"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "incorrect data"}), 400

    row = BrandCapacity.query.filter_by(store_id=store_id, brand=brand).first()
    if row:
        row.capacity = new_capacity
    else:
        row = BrandCapacity(store_id=store_id, brand=brand, capacity=new_capacity)
        db.session.add(row)

    db.session.commit()
    return jsonify({"brand": row.brand, "capacity": row.capacity})
