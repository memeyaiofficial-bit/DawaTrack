"""add medicine_requests and dispense_records tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-11 00:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'medicine_requests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('patient_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('medicine_name', sa.String(length=200), nullable=False),
        sa.Column('dosage', sa.String(length=60), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'replied', 'fulfilled', 'unavailable', name='request_status'), nullable=False, server_default='pending'),
        sa.Column('pharmacy_reply', sa.Text(), nullable=True),
        sa.Column('pharmacist_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'dispense_records',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('patient_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('patient_name', sa.String(length=120), nullable=False),
        sa.Column('pharmacist_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('medicine_name', sa.String(length=200), nullable=False),
        sa.Column('dosage', sa.String(length=60), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.Enum('dispensed', 'pending', 'unavailable', name='dispense_status'), nullable=False, server_default='dispensed'),
        sa.Column('smart_card', sa.String(length=20), nullable=False, server_default='none'),
        sa.Column('discount_pct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('dispense_records')
    op.drop_table('medicine_requests')
    op.execute("DROP TYPE IF EXISTS dispense_status")
    op.execute("DROP TYPE IF EXISTS request_status")
