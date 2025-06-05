"""User (Operators) entity."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from .base import BaseUUIDModel, SoftDeleteMixin, TimeStampedMixin

if TYPE_CHECKING:
    from .audit_log import AuditLog
    from .tally_session import TallySession
    from .voter import Voter


class User(BaseUUIDModel, TimeStampedMixin, SoftDeleteMixin, table=True):
    """Operator user entity."""

    __tablename__ = "users"

    username: str = Field(unique=True, index=True)
    password_hash: str
    full_name: str
    role: str = Field(default="operator")
    is_active: bool = Field(default=True)

    # Relationships - specify foreign_keys to resolve ambiguity
    voted_voters: Voter = Relationship(
        back_populates="voted_by_operator",
        sa_relationship_kwargs={"foreign_keys": "[Voter.voted_by_operator_id]"}
    )
    tally_sessions: TallySession = Relationship(
        back_populates="operator",
        sa_relationship_kwargs={"foreign_keys": "[TallySession.operator_id]"}
    )
    recounted_tally_sessions: TallySession = Relationship(
        back_populates="recount_operator",
        sa_relationship_kwargs={"foreign_keys": "[TallySession.recount_operator_id]"}
    )
    audit_logs: AuditLog = Relationship(
        back_populates="operator",
        sa_relationship_kwargs={"foreign_keys": "[AuditLog.operator_id]"}
    )
