from models import Store, db
from app import app


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
    ("ICR_Shoes TB_Galery", "store"),
    ("Bambino_2 EastPoint", "store"),
    ("Bata_ Batu_2_Metro", "store"),
    ("Bata_ Batu_Gamsax", "store"),
    ("Bata_ Kutsi", "store"),
    ("Bata_ Zugd_Mall", "store"),
    ("Bata_1 Chavch", "store"),
    ("Bata_2 Vazha", "store"),
    ("Bata_7 EastPoint", "store"),
    ("Bata_9 Sab_CityMall", "store"),
    ("BataScarp Gld_CityMall", "store"),
    ("Replay Sab_CityMall", "store"),
    ("Replay_Outlet", "store"),
    ("Scar_ Bat_Gamsax", "store"),
    ("Scar_2 Sab_CityMall", "store"),
    ("WH_Konserv", "warehouse"),
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
    with app.app_context():
        seed_stores()
