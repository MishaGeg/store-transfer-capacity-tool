from flask import Blueprint, jsonify, render_template, request, current_app
from sqlalchemy.exc import SQLAlchemyError
from catalog import get_brand_group_names
from models import BrandCapacity, Store, db

from permissions import supply_chain_required

capacities_bp = Blueprint("capacities", __name__)


def capacity_list():
    """Include every store and catalog group; None means capacity is not set."""
    values = {}
    for row in BrandCapacity.query.all():
        values[(row.store_id, row.brand)] = row.capacity

    brand_groups = get_brand_group_names()
    stores = Store.query.order_by(Store.name).all()
    result = []

    for store in stores:
        capacities = {}
        for brand_group in brand_groups:
            capacities[brand_group] = values.get((store.id, brand_group))

        result.append(
            {
                "store_id": store.id,
                "store_name": store.name,
                "capacities": capacities,
            }
        )

    return result


@capacities_bp.route("/edit-capacities")
@supply_chain_required
def edit_capacities():
    return render_template("edit-capacities.html")


@capacities_bp.route("/capacities", methods=["GET"])
@supply_chain_required
def show_capacities():
    return jsonify(capacity_list())


@capacities_bp.route("/capacities/<int:store_id>/<brand>", methods=["PUT"])
@supply_chain_required
def update_capacities(store_id, brand):
    if (
        not 1 <= store_id <= 2_147_483_647
        or brand not in get_brand_group_names()
        or db.session.get(Store, store_id) is None
    ):
        return jsonify({"error": "wrong store/brand name"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return {"error": "JSON body must be an object"}, 400

    new_capacity = data.get("capacity")

    if not isinstance(new_capacity, int) or isinstance(new_capacity, bool):
        return {"error": "capacity must be an integer"}, 400

    if new_capacity < 0:
        return {"error": "capacity cannot be negative"}, 400
    if new_capacity > 2_147_483_647:
        return {"error": "capacity cannot exceed 2147483647"}, 400

    row = BrandCapacity.query.filter_by(store_id=store_id, brand=brand).first()
    if row:
        row.capacity = new_capacity
    else:
        row = BrandCapacity(store_id=store_id, brand=brand, capacity=new_capacity)
        db.session.add(row)
    try:
        db.session.commit()
    except SQLAlchemyError:
        current_app.logger.exception("Could not save capacity")
        db.session.rollback()
        return {"error": "Could not save capacity. Please try again."}, 500
    return jsonify({"brand": row.brand, "capacity": row.capacity})
