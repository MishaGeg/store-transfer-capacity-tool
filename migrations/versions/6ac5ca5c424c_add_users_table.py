"""Add users table

Revision ID: 6ac5ca5c424c
Revises: daad63f48f98
Create Date: 2026-09-23 17:07:49.826827

"""
from alembic import op
import sqlalchemy as sa



revision = '6ac5ca5c424c'
down_revision = 'daad63f48f98'
branch_labels = None
depends_on = None


def upgrade():

    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=120), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.CheckConstraint("type IN ('admin', 'manager','viewer')", name='check_user_type'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )



def downgrade():

    op.drop_table('users')
