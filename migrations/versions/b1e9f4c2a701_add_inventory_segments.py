"""add adult and kids inventory segments

Revision ID: b1e9f4c2a701
Revises: 2392affb73da
"""
from alembic import op
import sqlalchemy as sa


revision = "b1e9f4c2a701"
down_revision = "2392affb73da"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("stock_snapshots", "capacities", "transfers"):
        op.add_column(table, sa.Column("segment", sa.String(length=10), nullable=True))
        op.execute(f"UPDATE {table} SET segment = 'ADULTS' WHERE segment IS NULL")
        op.alter_column(table, "segment", nullable=False)

    with op.batch_alter_table("stock_snapshots") as batch:
        batch.drop_constraint("unique_stock_snapshot_store_brand_category", type_="unique")
        batch.create_unique_constraint(
            "unique_stock_snapshot_store_brand_category_segment",
            ["store_id", "brand", "category", "segment"],
        )
        batch.create_check_constraint("check_stock_snapshot_segment", "segment IN ('ADULTS', 'KIDS')")

    with op.batch_alter_table("capacities") as batch:
        batch.drop_constraint("unique_brand_capacity_store_id_brand", type_="unique")
        batch.create_unique_constraint(
            "unique_brand_capacity_store_id_brand_segment", ["store_id", "brand", "segment"]
        )
        batch.create_check_constraint("check_capacity_segment", "segment IN ('ADULTS', 'KIDS')")

    with op.batch_alter_table("transfers") as batch:
        batch.create_check_constraint("check_transfer_segment", "segment IN ('ADULTS', 'KIDS')")


def downgrade():
    with op.batch_alter_table("transfers") as batch:
        batch.drop_constraint("check_transfer_segment", type_="check")
    with op.batch_alter_table("capacities") as batch:
        batch.drop_constraint("check_capacity_segment", type_="check")
        batch.drop_constraint("unique_brand_capacity_store_id_brand_segment", type_="unique")
        batch.create_unique_constraint("unique_brand_capacity_store_id_brand", ["store_id", "brand"])
    with op.batch_alter_table("stock_snapshots") as batch:
        batch.drop_constraint("check_stock_snapshot_segment", type_="check")
        batch.drop_constraint("unique_stock_snapshot_store_brand_category_segment", type_="unique")
        batch.create_unique_constraint("unique_stock_snapshot_store_brand_category", ["store_id", "brand", "category"])
    for table in ("transfers", "capacities", "stock_snapshots"):
        op.drop_column(table, "segment")
