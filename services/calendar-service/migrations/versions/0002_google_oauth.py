"""per-participant calendar links + google_credentials

Revision ID: 0002_google_oauth
Revises: 0001_initial
Create Date: 2026-06-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_google_oauth"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # calendar_links: a booking now maps to one event PER participant.
    op.add_column(
        "calendar_links",
        sa.Column("user_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "calendar_links",
        sa.Column("calendar_id", sa.String(length=256), nullable=False, server_default="primary"),
    )
    # Widen the event id column for real Google event ids.
    op.alter_column(
        "calendar_links",
        "external_event_id",
        type_=sa.String(length=256),
        existing_type=sa.String(length=128),
        existing_nullable=False,
    )
    # booking_id is no longer unique on its own.
    op.drop_index("ix_calendar_links_booking_id", table_name="calendar_links")
    op.create_index("ix_calendar_links_booking_id", "calendar_links", ["booking_id"])
    op.create_index("ix_calendar_links_user_id", "calendar_links", ["user_id"])
    op.create_unique_constraint(
        "uq_calendar_links_booking_user", "calendar_links", ["booking_id", "user_id"]
    )

    op.create_table(
        "google_credentials",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("google_email", sa.String(length=255), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("google_credentials")
    op.drop_constraint(
        "uq_calendar_links_booking_user", "calendar_links", type_="unique"
    )
    op.drop_index("ix_calendar_links_user_id", table_name="calendar_links")
    op.drop_index("ix_calendar_links_booking_id", table_name="calendar_links")
    op.create_index(
        "ix_calendar_links_booking_id", "calendar_links", ["booking_id"], unique=True
    )
    op.alter_column(
        "calendar_links",
        "external_event_id",
        type_=sa.String(length=128),
        existing_type=sa.String(length=256),
        existing_nullable=False,
    )
    op.drop_column("calendar_links", "calendar_id")
    op.drop_column("calendar_links", "user_id")
