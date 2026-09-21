from models import Store, db
from flask import Blueprint, jsonify



stores_bp =Blueprint("stores", __name__)

@stores_bp.route("/stores", methods = ["GET"])
def show_stores():
    stores = [{"id": s.id, "name": s.name, "type": s.type} for s in Store.query.all()]
    return jsonify(stores)



STORES = [
    ("ShoeGal_ Chavch", "store"),
    ("ICR_Shoes", "store"),
    ("WH_Gamarj", "warehouse"),
    ("ICR_Shoes East_Point", "store"),
    ("ICR_Shoes_ Batu_GR_Mall", "store"),
    ("Ecco_Geox_Out", "store"),
    ("ICR_Shoes TB_Mall", "store"),
    ("ShoeGal_9 Sab_CityMall", "store"),
    ("ShoeGal_10 Vazha", "store"),
    ("ShoeGal_ Batu_Gamsax", "store"),
    ("ICR_Shoes_2", "store"),
    ("ICR_Shoes_TB_Galery", "store"),
]

def seed_stores():
    created = 0
    updated = 0

    for name, store_type in STORES:
        existing = Store.query.filter_by(name=name).first()

        if existing:
            existing.type = store_type
            updated += 1
        else:
            db.session.add(Store(name=name, type=store_type))
            created += 1


    db.session.commit()
    print(f"Done. Created: {created}, Updated: {updated}")

if __name__ == "__main__":
    from app import app
    with app.app_context():
        seed_stores()