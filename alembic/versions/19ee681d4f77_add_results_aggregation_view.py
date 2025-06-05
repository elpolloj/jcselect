"""Add results aggregation view

Revision ID: 19ee681d4f77
Revises: 48d1d8da74af
Create Date: 2025-06-02 12:19:42.085815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '19ee681d4f77'
down_revision: Union[str, None] = '48d1d8da74af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with results aggregation view."""
    # Note: candidate_id and deleted_at columns already exist in the schema
    
    # ### Add missing ballot_type and ballot_number columns to tally_lines ###
    # These should have been added by 48d1d8da74af but are missing from the database
    try:
        op.add_column('tally_lines', sa.Column('ballot_type', sa.String(length=20), nullable=False, server_default='normal'))
        op.create_index(op.f('ix_tally_lines_ballot_type'), 'tally_lines', ['ballot_type'], unique=False)
    except Exception:
        # Column may already exist in some databases
        pass
    
    try:
        op.add_column('tally_lines', sa.Column('ballot_number', sa.Integer(), nullable=True))
        op.create_index(op.f('ix_tally_lines_ballot_number'), 'tally_lines', ['ballot_number'], unique=False)
    except Exception:
        # Column may already exist in some databases
        pass
    
    # ### Create results aggregation view ###
    op.execute("""
        CREATE VIEW v_results_aggregate AS
        SELECT
            ts.pen_id,
            tl.party_id,
            tl.candidate_id,
            tl.ballot_type,
            SUM(CASE WHEN tl.deleted_at IS NULL THEN tl.vote_count ELSE 0 END) AS votes,
            COUNT(CASE WHEN tl.deleted_at IS NULL THEN tl.id ELSE NULL END) AS ballot_count,
            MAX(tl.updated_at) AS last_updated
        FROM tally_lines tl
        JOIN tally_sessions ts ON tl.tally_session_id = ts.id
        WHERE ts.deleted_at IS NULL
        GROUP BY ts.pen_id, tl.party_id, tl.candidate_id, tl.ballot_type
    """)
    
    # ### Add performance index for results aggregation ###
    op.create_index(
        'idx_results_aggregate_pen_party', 
        'tally_lines', 
        ['tally_session_id', 'party_id', 'candidate_id'],
        postgresql_where=sa.text('deleted_at IS NULL'),
        sqlite_where=sa.text('deleted_at IS NULL')
    )


def downgrade() -> None:
    """Downgrade schema by removing results aggregation view."""
    # ### Drop performance index ###
    op.drop_index('idx_results_aggregate_pen_party', table_name='tally_lines')
    
    # ### Drop results aggregation view ###
    op.execute("DROP VIEW IF EXISTS v_results_aggregate")
    
    # ### Remove ballot columns if they were added by this migration ###
    # Note: We won't remove these as they might be needed by other parts of the system
