"""simplify brand capacities

Revision ID: e4c7a2d9f610
Revises: b1e9f4c2a701
"""
from alembic import op
import sqlalchemy as sa


revision = "e4c7a2d9f610"
down_revision = "b1e9f4c2a701"
branch_labels = None
depends_on = None


def upgrade():
    # Non-adult rows were never read by the application.
    op.execute("DELETE FROM capacities WHERE segment <> 'ADULTS'")
    with op.batch_alter_table("capacities") as batch:
        batch.drop_constraint("check_capacity_segment", type_="check")
        batch.drop_constraint("unique_brand_capacity_store_id_brand_segment", type_="unique")
        batch.drop_column("segment")
        batch.create_unique_constraint(
            "unique_brand_capacity_store_id_brand", ["store_id", "brand"]
        )


def downgrade():
    with op.batch_alter_table("capacities") as batch:
        batch.drop_constraint("unique_brand_capacity_store_id_brand", type_="unique")
        batch.add_column(
            sa.Column(
                "segment",
                sa.String(length=10),
                nullable=False,
                server_default="ADULTS",
            )
        )
        batch.create_unique_constraint(
            "unique_brand_capacity_store_id_brand_segment",
            ["store_id", "brand", "segment"],
        )
        batch.create_check_constraint(
            "check_capacity_segment", "segment IN ('ADULTS', 'KIDS')"
        )
