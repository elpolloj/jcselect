"""add_search_indexes_for_voter_optimization

Revision ID: a38a64aee2cc
Revises: 52569a9164c7
Create Date: 2025-05-29 11:23:56.560051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a38a64aee2cc'
down_revision: Union[str, None] = '52569a9164c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add search performance indexes."""
    # Index on voter_number for exact and partial number matching
    op.create_index('idx_voter_number', 'voters', ['voter_number'])
    
    # Index on full_name for name search
    op.create_index('idx_voter_full_name', 'voters', ['full_name'])
    
    # Index on father_name for father name search
    op.create_index('idx_voter_father_name', 'voters', ['father_name'])
    
    # Composite index for combined searches
    op.create_index('idx_voter_search_composite', 'voters', ['voter_number', 'full_name'])


def downgrade() -> None:
    """Downgrade schema - Remove search indexes."""
    # Drop indexes in reverse order
    op.drop_index('idx_voter_search_composite', table_name='voters')
    op.drop_index('idx_voter_father_name', table_name='voters')
    op.drop_index('idx_voter_full_name', table_name='voters')
    op.drop_index('idx_voter_number', table_name='voters')
