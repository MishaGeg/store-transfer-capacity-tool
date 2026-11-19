from flask import Blueprint, request, jsonify, render_template, current_app
from models import BrandCapacity, PlannedTransfer, StockSnapshot, db, Store
from datetime import datetime, timedelta
from permissions import supply_chain_required
from sqlalchemy import tuple_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import aliased
from catalog import AGE_GROUPS, get_brand_age_group_pairs, get_brand_group, get_brands_by_age_group
from flask_login import login_required

transfers_bp = Blueprint("transfers", __name__)


@transfers_bp.route("/transfers-page")
@supply_chain_required
def transfers_page():
    brands_by_segment = {}

    for age_group in AGE_GROUPS:
        brands_by_segment[age_group] = get_brands_by_age_group(age_group)

    return render_template("transfers.html", brands_by_segment=brands_by_segment)


def store_data(store):
    return {"id": store.id, "name": store.name, "type": store.type}


@transfers_bp.route("/transfer-options")
@supply_chain_required
def transfer_options():
    """Return grid stores and advisory free space for a catalog pair."""
    age_group = request.args.get("segment", "").upper()
    brand = request.args.get("brand", "").strip().upper()
    brand_group = get_brand_group(brand, age_group)
    if age_group not in AGE_GROUPS or brand_group is None:
        return jsonify({"error": "valid brand and segment are required"}), 400

    stock_rows = (
        db.session.query(StockSnapshot.store_id)
        .filter(
            StockSnapshot.brand == brand,
            StockSnapshot.segment == age_group,
            StockSnapshot.category == "FOOTWEAR",
            StockSnapshot.quantity > 0,
        )
        .distinct()
        .all()
    )

    source_ids = set()
    for row in stock_rows:
        source_ids.add(row.store_id)

    capacity_rows = BrandCapacity.query.filter_by(brand=brand_group).all()
    capacities = {}
    for capacity in capacity_rows:
        capacities[capacity.store_id] = capacity

    stores = Store.query.order_by(Store.name).all()
    sources = []
    destinations = []

    for store in stores:

        is_warehouse = store.type == "warehouse"

        if store.id in source_ids or is_warehouse:
            sources.append(store_data(store))

        capacity = capacities.get(store.id)

        if is_warehouse or (capacity is not None and capacity.capacity > 0):
            destination = store_data(store)
            if capacity is not None:
                destination["free_space"] = available_space(capacity)
            else:

                destination["free_space"] = None
            destinations.append(destination)

    return jsonify({"sources": sources, "destinations": destinations})


def available_space(capacity_row):
    """Subtract group footwear stock and recent inbound plans from capacity.

    Outbound plans do not reduce the recorded stock. Negative results indicate
    a capacity shortfall and are returned as advisory values.
    """
    pairs = get_brand_age_group_pairs(capacity_row.brand)

    cutoff = datetime.now() - timedelta(days=5)

    incoming_transfers = PlannedTransfer.query.filter(
        PlannedTransfer.submitted_at > cutoff,
        PlannedTransfer.to_store_id == capacity_row.store_id,

        tuple_(PlannedTransfer.brand, PlannedTransfer.segment).in_(pairs),
    ).all()

    recent_transfers = 0
    for transfer in incoming_transfers:
        recent_transfers += transfer.quantity

    stock_rows = StockSnapshot.query.filter(
        StockSnapshot.store_id == capacity_row.store_id,
        StockSnapshot.category == "FOOTWEAR",
        tuple_(StockSnapshot.brand, StockSnapshot.segment).in_(pairs),
    ).all()

    current_stock = 0
    for stock in stock_rows:
        current_stock += stock.quantity

    return capacity_row.capacity - current_stock - recent_transfers


@transfers_bp.route("/transfers", methods=["POST"])
@supply_chain_required
def create_transfers():
    """Validate rows individually and commit accepted rows together.

    Return 201 for full success, 207 for partial success, or 400 if none pass
    validation. Row errors use zero-based indexes into the submitted list.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON body must be an object"}), 400
    transfer_list = data.get("transfers")
    if not isinstance(transfer_list, list):
        return jsonify({"error": "transfers must be a list"}), 400
    existing_store_ids = {store.id for store in Store.query.all()}
    errors = []
    successful_transfers = []
    required = ("brand", "quantity", "segment", "from_store_id", "to_store_id")
    for row_num, t in enumerate(transfer_list):
        if not isinstance(t, dict):
            errors.append({"index": row_num, "error": "row must be an object"})
            continue
        missing = False
        for key in required:
            if key not in t:
                missing = True
        if missing:
            errors.append({"index": row_num, "error": "missing data"})
            continue
        if not isinstance(t["quantity"], int) or isinstance(t["quantity"], bool):
            errors.append({"index": row_num, "error": "quantity must be an integer"})
            continue
        if not isinstance(t["segment"], str) or t["segment"] not in AGE_GROUPS:
            errors.append({"index": row_num, "error": "segment must be ADULTS or KIDS"})
            continue
        if not isinstance(t["brand"], str):
            errors.append({"index": row_num, "error": "brand must be a string"})
            continue
        if get_brand_group(t["brand"], t["segment"]) is None:
            errors.append(
                {"index": row_num, "error": "invalid brand/segment combination"}
            )
            continue
        if not 1 <= t["quantity"] <= 2_147_483_647:
            errors.append({"index": row_num, "error": "quantity must be between 1 and 2147483647"})
            continue
        if (
            not isinstance(t["from_store_id"], int)
            or isinstance(t["from_store_id"], bool)
            or not isinstance(t["to_store_id"], int)
            or isinstance(t["to_store_id"], bool)
        ):
            errors.append({"index": row_num, "error": "store IDs must be integers"})
            continue
        if (
            t["from_store_id"] not in existing_store_ids
            or t["to_store_id"] not in existing_store_ids
        ):
            errors.append({"index": row_num, "error": "source or destination store does not exist"})
            continue
        if t["from_store_id"] == t["to_store_id"]:
            errors.append({"index": row_num, "error": "source and destination stores must differ"})
            continue
        new_transfer = PlannedTransfer(
            brand=t["brand"],
            quantity=t["quantity"],
            segment=t["segment"],
            submitted_at=datetime.now(),
            from_store_id=t["from_store_id"],
            to_store_id=t["to_store_id"],
        )
        successful_transfers.append(new_transfer)
    try:
        for t in successful_transfers:
            db.session.add(t)
        db.session.commit()
    except SQLAlchemyError:
        current_app.logger.exception("Could not save transfers")
        db.session.rollback()
        return {"error": "Could not save transfers. Please try again."}, 500
    if successful_transfers and errors:
        status_code = 207
    elif successful_transfers:
        status_code = 201
    else:
        status_code = 400
    return (
        jsonify(
            {
                "errors": errors,
                "created": [
                    {
                        "id": s.id,
                        "brand": s.brand,
                        "quantity": s.quantity,
                        "segment": s.segment,
                        "submitted_at": s.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "from_store_id": s.from_store_id,
                        "to_store_id": s.to_store_id,
                    }
                    for s in successful_transfers
                ],
            }
        ),
        status_code,
    )


@transfers_bp.route("/transfers/<int:id>", methods=["DELETE"])
@supply_chain_required
def delete_transfer(id):
    if not 1 <= id <= 2_147_483_647:
        return jsonify({"error": "wrong transfer id"}), 404
    result = PlannedTransfer.query.filter_by(id=id).first()
    if not result:
        return jsonify({"error": "wrong transfer id"}), 404
    try:
        db.session.delete(result)
        db.session.commit()
    except SQLAlchemyError:
        current_app.logger.exception("Could not delete transfer")
        db.session.rollback()
        return {"error": "Could not delete transfer. Please try again."}, 500
    return jsonify({"deleted_id": id, "status": "success"}), 200


@transfers_bp.route("/transfers", methods=["GET"])
@supply_chain_required
def show_transfers():
    transfers = [
        {
            "id": s.id,
            "brand": s.brand,
            "quantity": s.quantity,
            "segment": s.segment,
            "submitted_at": s.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
            "from_store_id": s.from_store_id,
            "to_store_id": s.to_store_id,
        }
        for s in PlannedTransfer.query.all()
    ]
    return jsonify(transfers)


@transfers_bp.route("/public-transfers")
@login_required
def public_transfers():
    return render_template("view-transfers.html")


@transfers_bp.route("/view-transfers", methods=["GET"])
@login_required
def view_transfers():

    cutoff = datetime.now() - timedelta(days=5)
    FromStore = aliased(Store)
    ToStore = aliased(Store)
    transfers = [
        {
            "id": s.id,
            "brand": s.brand,
            "quantity": s.quantity,
            "segment": s.segment,
            "submitted_at": s.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
            "from_store_name": f.name,
            "to_store_name": t.name,
            "from_store_id": s.from_store_id,
            "to_store_id": s.to_store_id,
        }
        for s, f, t in db.session.query(PlannedTransfer, FromStore, ToStore)
        .join(FromStore, PlannedTransfer.from_store_id == FromStore.id)
        .join(ToStore, PlannedTransfer.to_store_id == ToStore.id)
        .filter(PlannedTransfer.submitted_at > cutoff)
        .all()
    ]
    return jsonify(transfers)
