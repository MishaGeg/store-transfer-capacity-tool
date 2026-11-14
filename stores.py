from models import Store
from flask import Blueprint, jsonify
from permissions import supply_chain_required


stores_bp = Blueprint("stores", __name__)

@stores_bp.route("/stores", methods = ["GET"])
@supply_chain_required
def show_stores():
    stores = [{"id": s.id, "name": s.name, "type": s.type} for s in Store.query.all()]
    return jsonify(stores)
