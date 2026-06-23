"""Ajouter type_vehicule et region_plaque à vehicules

Revision ID: 002
Revises: 001
Create Date: 2026-06-22
"""
from alembic import op

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE vehicules ADD COLUMN IF NOT EXISTS type_vehicule TEXT")
    op.execute("ALTER TABLE vehicules ADD COLUMN IF NOT EXISTS region_plaque TEXT")


def downgrade():
    op.execute("ALTER TABLE vehicules DROP COLUMN IF EXISTS type_vehicule")
    op.execute("ALTER TABLE vehicules DROP COLUMN IF EXISTS region_plaque")
