"""initial calendar schema (calendar_links)

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calendar_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("external_event_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_calendar_links_booking_id", "calendar_links", ["booking_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_calendar_links_booking_id", table_name="calendar_links")
    op.drop_table("calendar_links")
