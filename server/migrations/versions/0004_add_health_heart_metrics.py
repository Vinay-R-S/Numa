"""add_health_heart_metrics

Revision ID: c4e6f1a9d2b3
Revises: b9a1f3c8e2d4
Create Date: 2026-05-22
"""
from alembic import op


revision = "c4e6f1a9d2b3"
down_revision = "b9a1f3c8e2d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.health_snapshots ADD COLUMN IF NOT EXISTS heart_rate_bpm REAL")
    op.execute("ALTER TABLE public.health_snapshots ADD COLUMN IF NOT EXISTS heart_points REAL")


def downgrade() -> None:
    op.execute("ALTER TABLE public.health_snapshots DROP COLUMN IF EXISTS heart_points")
    op.execute("ALTER TABLE public.health_snapshots DROP COLUMN IF EXISTS heart_rate_bpm")
