from models import Store, db
from flask import Blueprint, jsonify



stores_bp =Blueprint("stores", __name__)

@stores_bp.route("/stores", methods = ["GET"])
def show_stores():
    stores = [{"id": s.id, "name": s.name, "type": s.type} for s in Store.query.all()]
    return jsonify(stores)
