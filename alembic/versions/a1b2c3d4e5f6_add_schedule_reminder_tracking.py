"""add last_reminder_sent_at to medication_schedules

Revision ID: a1b2c3d4e5f6
Revises: 6f3b2996b568
Create Date: 2026-08-11 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6f3b2996b568'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'medication_schedules',
        sa.Column('last_reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('medication_schedules', 'last_reminder_sent_at')
