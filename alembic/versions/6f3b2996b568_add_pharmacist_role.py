"""add pharmacist role

Revision ID: 6f3b2996b568
Revises: 730b285bdd33
Create Date: 2026-07-22 16:22:22.436100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f3b2996b568'
down_revision: Union[str, None] = '730b285bdd33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres enums can't be altered inside a transaction in older PG
    # versions, so this runs as its own statement outside a DDL batch.
    # ADD VALUE IF NOT EXISTS keeps this migration safe to re-run.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'pharmacist'")


def downgrade() -> None:
    # Postgres does not support removing a value from an enum type
    # directly. Rebuild the enum without 'pharmacist' instead.
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('patient', 'doctor')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role "
        "USING role::text::user_role"
    )
    op.execute("DROP TYPE user_role_old")