"""Tally counting enhancements

Revision ID: 48d1d8da74af
Revises: 56f069e8711f
Create Date: 2025-01-22 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '48d1d8da74af'
down_revision: Union[str, None] = '56f069e8711f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with tally counting enhancements."""
    # ### Tally Sessions enhancements ###
    # Add ballot tracking
    op.add_column('tally_sessions', sa.Column('ballot_number', sa.Integer(), nullable=False, server_default='0'))
    
    # Add recount tracking
    op.add_column('tally_sessions', sa.Column('recounted_at', sa.DateTime(), nullable=True))
    op.add_column('tally_sessions', sa.Column('recount_operator_id', sqlmodel.sql.sqltypes.GUID(), nullable=True))
    
    # Add index for recount operations
    op.create_index(op.f('ix_tally_sessions_recounted_at'), 'tally_sessions', ['recounted_at'], unique=False)
    op.create_index(op.f('ix_tally_sessions_recount_operator_id'), 'tally_sessions', ['recount_operator_id'], unique=False)
    
    # ### Tally Lines enhancements ###
    # Add ballot type tracking
    op.add_column('tally_lines', sa.Column('ballot_type', sa.String(length=20), nullable=False, server_default='normal'))
    
    # Add ballot number tracking
    op.add_column('tally_lines', sa.Column('ballot_number', sa.Integer(), nullable=True))
    
    # Add indexes for performance
    op.create_index(op.f('ix_tally_lines_ballot_type'), 'tally_lines', ['ballot_type'], unique=False)
    op.create_index(op.f('ix_tally_lines_ballot_number'), 'tally_lines', ['ballot_number'], unique=False)


def downgrade() -> None:
    """Downgrade schema by removing tally counting enhancements."""
    # ### Remove Tally Lines enhancements ###
    op.drop_index(op.f('ix_tally_lines_ballot_number'), table_name='tally_lines')
    op.drop_index(op.f('ix_tally_lines_ballot_type'), table_name='tally_lines')
    op.drop_column('tally_lines', 'ballot_number')
    op.drop_column('tally_lines', 'ballot_type')
    
    # ### Remove Tally Sessions enhancements ###
    op.drop_index(op.f('ix_tally_sessions_recount_operator_id'), table_name='tally_sessions')
    op.drop_index(op.f('ix_tally_sessions_recounted_at'), table_name='tally_sessions')
    op.drop_column('tally_sessions', 'recount_operator_id')
    op.drop_column('tally_sessions', 'recounted_at')
    op.drop_column('tally_sessions', 'ballot_number')
