from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(20), nullable=False)

    __table_args__ = (
        db.CheckConstraint("type IN ('store', 'warehouse')", name="check_store_type"),
    )

class StockSnapshot(db.Model):
    __tablename__ = "stock_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    snapshot_date = db.Column(db.DateTime, nullable=False)

    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)


    __table_args__ = (
        db.UniqueConstraint(
            "store_id", "brand", "category",
            name="unique_stock_snapshot_store_brand_category"
        ),
    )

class BrandCapacity(db.Model):
    __tablename__ = "capacities"

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)

    __table_args__ = (
            db.UniqueConstraint(
                "store_id", "brand",
                name="unique_brand_capacity_store_id_brand"
            ),
        )       