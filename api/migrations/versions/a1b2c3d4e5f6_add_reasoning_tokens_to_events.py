# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""add reasoning_tokens to events

Revision ID: a1b2c3d4e5f6
Revises: f34a57eb946e
Create Date: 2026-03-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f34a57eb946e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add reasoning_tokens column to events table."""
    op.add_column(
        'events',
        sa.Column('reasoning_tokens', sa.Integer(), nullable=True, server_default='0'),
    )


def downgrade() -> None:
    """Remove reasoning_tokens column from events table."""
    op.drop_column('events', 'reasoning_tokens')
