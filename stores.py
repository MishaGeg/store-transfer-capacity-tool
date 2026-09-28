from models import Store
from flask import Blueprint, jsonify
from flask_login import login_required


stores_bp = Blueprint("stores", __name__)

@stores_bp.route("/stores", methods = ["GET"])
@login_required
def show_stores():
    stores = [{"id": s.id, "name": s.name, "type": s.type} for s in Store.query.all()]
    return jsonify(stores)
