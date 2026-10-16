"""add description + meeting_link to slots

Revision ID: 0002_slot_meeting_fields
Revises: 0001_initial
Create Date: 2026-06-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_slot_meeting_fields"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("slots", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("slots", sa.Column("meeting_link", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("slots", "meeting_link")
    op.drop_column("slots", "description")
