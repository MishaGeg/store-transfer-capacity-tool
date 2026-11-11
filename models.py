from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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
    segment = db.Column(db.String(10), nullable=False, default="ADULTS")
    quantity = db.Column(db.Integer, nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    snapshot_date = db.Column(db.DateTime, nullable=False)

    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)


    __table_args__ = (
        db.CheckConstraint("segment IN ('ADULTS', 'KIDS')", name="check_stock_snapshot_segment"),
        db.UniqueConstraint("store_id", "brand", "category", "segment", name="unique_stock_snapshot_store_brand_category_segment"),
        )

class BrandCapacity(db.Model):
    __tablename__ = "capacities"

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)

    __table_args__ = (
            db.UniqueConstraint("store_id", "brand", name="unique_brand_capacity_store_id_brand"),
            )

class PlannedTransfer(db.Model):
    __tablename__ = "transfers"

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    segment = db.Column(db.String(10), nullable=False, default="ADULTS")
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    from_store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    to_store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)

    __table_args__ = (
        db.CheckConstraint("from_store_id != to_store_id", name="ck_transfer_different_stores"),
        db.CheckConstraint("quantity > 0", name="ck_transfer_positive_quantity"),
        db.CheckConstraint("segment IN ('ADULTS', 'KIDS')", name="check_transfer_segment"),
        )
