from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(20), nullable=False)

    __table_args__ = ((
        db.CheckConstraint("type IN ('store', 'warehouse')", name="check_store_type")
        ),)

class StockSnapshot(db.Model):
    __tablename__ = "stock_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    snapshot_date = db.Column(db.DateTime, nullable=False)

    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)


    __table_args__ = ((
        db.UniqueConstraint("store_id", "brand", "category", name="unique_stock_snapshot_store_brand_category")
        ),)

class BrandCapacity(db.Model):
    __tablename__ = "capacities"

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)

    __table_args__ = ((
            db.UniqueConstraint("store_id", "brand", name="unique_brand_capacity_store_id_brand")
            ),)

class PlannedTransfer(db.Model):
    __tablename__ = "transfers"

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    from_store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    to_store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)

    __table_args__ = (
        db.CheckConstraint("from_store_id != to_store_id", name="ck_transfer_different_stores"),
        db.CheckConstraint("quantity > 0", name="ck_transfer_positive_quantity"),
        )           