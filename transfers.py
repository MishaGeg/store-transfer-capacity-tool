from flask import Blueprint, request, jsonify, render_template
from models import PlannedTransfer, db, Store
from datetime import datetime
from flask_login import login_required
from sqlalchemy.orm import aliased


transfers_bp = Blueprint("transfers", __name__)

@transfers_bp.route("/transfers-page")
@login_required
def transfers_page():
    return render_template("transfers.html")

@transfers_bp.route("/public-transfers")
def public_transfers():
    return render_template("view-transfers.html")


@transfers_bp.route("/transfers", methods=["POST"])
@login_required
def create_transfers():
    data = request.get_json(silent=True) or {}
    transfer_list = data.get("transfers")
    if not isinstance(transfer_list, list):
        return jsonify({"error": "transfers must be a list"}), 400
    errors = []
    successful_transfers = []
    for row_num, t in enumerate(transfer_list):
        if t["quantity"] <= 0 or t["from_store_id"] == t["to_store_id"]:
            errors.append({"index": row_num, "error": "quantity must be > 0 or from/to stores must differ"})
            continue
        else:
            new_transfer = PlannedTransfer(
                brand = t["brand"],
                quantity = t["quantity"], 
                submitted_at = datetime.now(), 
                from_store_id = t["from_store_id"], 
                to_store_id = t["to_store_id"]
            )
            successful_transfers.append(new_transfer)      
    for t in successful_transfers:    
        db.session.add(t)
    db.session.commit()
    if successful_transfers and errors:
        status_code = 207 
    elif successful_transfers:
        status_code = 201  
    else:
        status_code = 400 
    return jsonify({
        "errors": errors,
        "created": [
            {
                "id": s.id,
                "brand": s.brand,
                "quantity": s.quantity,
                "submitted_at": s.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
                "from_store_id": s.from_store_id,
                "to_store_id": s.to_store_id
            }
            for s in successful_transfers
        ]
    }), status_code



@transfers_bp.route("/transfers/<int:id>", methods=["DELETE"])
@login_required
def delete_transfer(id):
    result = PlannedTransfer.query.filter_by(id = id).first()
    if not result:
        return jsonify({"error": "wrong transfer id"}), 404
    db.session.delete(result)
    db.session.commit()
    return jsonify({"deleted_id": id, "status": "success"}), 200

@transfers_bp.route("/transfers", methods = ["GET"])
def show_transfers():
    transfers = [
        {
            "id": s.id,
            "brand": s.brand, 
            "quantity": s.quantity,
            "submitted_at": s.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
            "from_store_id": s.from_store_id,
            "to_store_id": s.to_store_id 
        } 
        for s in PlannedTransfer.query.all()
    ]
    return jsonify(transfers)

@transfers_bp.route("/view-transfers", methods=["GET"])
def view_transfers():
    FromStore = aliased(Store)
    ToStore = aliased(Store)
    transfers = [
            {
                "id": s.id,
                "brand": s.brand, 
                "quantity": s.quantity,
                "submitted_at": s.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
                "from_store_name": f.name,
                "to_store_name": t.name,
                "from_store_id": s.from_store_id,
                "to_store_id": s.to_store_id 
            } 
            for s, f, t in db.session.query(PlannedTransfer, FromStore, ToStore)
            .join(FromStore,  PlannedTransfer.from_store_id == FromStore.id)
            .join(ToStore,  PlannedTransfer.to_store_id == ToStore.id)
            .all()
    ]
    return jsonify(transfers)    


