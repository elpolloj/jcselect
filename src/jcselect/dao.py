"""Data Access Objects for jcselect."""
from __future__ import annotations

from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from jcselect.models import (
    AuditLog,
    Party,
    Pen,
    TallyLine,
    TallySession,
    Voter,
)
from jcselect.models.base import BaseUUIDModel
from jcselect.models.sync_schemas import ChangeOperation
from jcselect.sync.queue import sync_queue

T = TypeVar("T", bound=BaseUUIDModel)


def _entity_to_dict(entity: BaseUUIDModel) -> dict[str, Any]:
    """
    Convert a SQLModel entity to a dictionary for sync.

    Args:
        entity: The entity to convert

    Returns:
        Dictionary representation of the entity
    """
    result = {}
    for field_name in entity.__class__.model_fields:
        value = getattr(entity, field_name)
        if isinstance(value, datetime):
            result[field_name] = value.isoformat()
        elif isinstance(value, UUID):
            result[field_name] = str(value)
        else:
            result[field_name] = value
    return result


def tally_line_to_dict(line: TallyLine) -> dict[str, Any]:
    """
    Convert a TallyLine entity to a dictionary for sync operations.

    Specifically handles TallyLine fields including ballot_type enum and
    UUID/datetime serialization for sync compatibility.

    Args:
        line: The TallyLine entity to convert

    Returns:
        Dictionary representation suitable for sync transmission
    """
    return {
        "id": str(line.id),
        "tally_session_id": str(line.tally_session_id),
        "party_id": str(line.party_id) if line.party_id else None,
        "vote_count": line.vote_count,
        "ballot_type": line.ballot_type.value if line.ballot_type else "normal",
        "ballot_number": line.ballot_number,
        "created_at": line.created_at.isoformat() if line.created_at else None,
        "updated_at": line.updated_at.isoformat() if line.updated_at else None,
        "deleted_at": line.deleted_at.isoformat() if line.deleted_at else None,
        "deleted_by": str(line.deleted_by) if line.deleted_by else None,
        "timestamp": line.timestamp.isoformat() if hasattr(line, 'timestamp') and line.timestamp else None,
    }


def upsert(model_instance: T, session: Session) -> T:
    """
    Generic upsert that works on both SQLite and MSSQL.

    Args:
        model_instance: SQLModel instance to upsert
        session: Database session

    Returns:
        The upserted model instance

    Raises:
        IntegrityError: If constraint violations occur
    """
    try:
        session.add(model_instance)
        session.flush()  # Get the ID without committing
        logger.debug(
            f"Upserted {type(model_instance).__name__} with ID {model_instance.id}"
        )
        return model_instance
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Upsert failed for {type(model_instance).__name__}: {e}")
        raise


def mark_voted(voter_id: UUID, operator_id: UUID, session: Session) -> Voter:
    """
    Atomic voter marking with audit trail.

    Args:
        voter_id: UUID of the voter to mark
        operator_id: UUID of the operator performing the action
        session: Database session

    Returns:
        Updated Voter instance

    Raises:
        ValueError: If voter not found or already voted
        IntegrityError: If database constraints are violated
    """
    # Get the voter
    voter = session.get(Voter, voter_id)
    if not voter:
        raise ValueError(f"Voter with ID {voter_id} not found")

    if voter.has_voted:
        raise ValueError(f"Voter {voter.voter_number} has already voted")

    # Store old values for audit
    old_values = {
        "has_voted": voter.has_voted,
        "voted_at": voter.voted_at,
        "voted_by_operator_id": voter.voted_by_operator_id,
    }

    # Update voter
    voter.has_voted = True
    voter.voted_at = datetime.utcnow()
    voter.voted_by_operator_id = operator_id

    new_values = {
        "has_voted": voter.has_voted,
        "voted_at": voter.voted_at.isoformat() if voter.voted_at else None,
        "voted_by_operator_id": str(voter.voted_by_operator_id),
    }

    try:
        session.add(voter)
        session.flush()

        # Create audit log
        audit_log = AuditLog(
            operator_id=operator_id,
            action="VOTER_MARKED",
            entity_type="Voter",
            entity_id=voter_id,
            old_values=old_values,
            new_values=new_values,
        )
        session.add(audit_log)
        session.flush()

        logger.info(
            f"Voter {voter.voter_number} marked as voted by operator {operator_id}"
        )
        return voter

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Failed to mark voter {voter_id} as voted: {e}")
        raise


def create_tally_session(
    pen_id: UUID, operator_id: UUID, session_name: str, session: Session
) -> TallySession:
    """
    Initialize counting session.

    Args:
        pen_id: UUID of the pen
        operator_id: UUID of the operator
        session_name: Name for the tally session
        session: Database session

    Returns:
        Created TallySession instance

    Raises:
        ValueError: If pen not found
        IntegrityError: If database constraints are violated
    """
    # Verify pen exists
    pen = session.get(Pen, pen_id)
    if not pen:
        raise ValueError(f"Pen with ID {pen_id} not found")

    # Create tally session
    tally_session = TallySession(
        pen_id=pen_id,
        operator_id=operator_id,
        session_name=session_name,
        started_at=datetime.utcnow(),
    )

    try:
        session.add(tally_session)
        session.flush()

        # Create audit log
        audit_log = AuditLog(
            operator_id=operator_id,
            action="TALLY_CREATED",
            entity_type="TallySession",
            entity_id=tally_session.id,
            old_values=None,
            new_values={
                "pen_id": str(pen_id),
                "session_name": session_name,
                "started_at": tally_session.started_at.isoformat(),
            },
        )
        session.add(audit_log)
        session.flush()

        logger.info(f"Created tally session '{session_name}' for pen {pen_id}")
        return tally_session

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Failed to create tally session: {e}")
        raise


def update_tally_line(
    session_id: UUID, party_id: UUID, vote_count: int, session: Session
) -> TallyLine:
    """
    Upsert vote counts for a party in a tally session.

    Args:
        session_id: UUID of the tally session
        party_id: UUID of the party
        vote_count: Number of votes
        session: Database session

    Returns:
        Updated or created TallyLine instance

    Raises:
        ValueError: If tally session or party not found, or invalid vote count
        IntegrityError: If database constraints are violated
    """
    if vote_count < 0:
        raise ValueError("Vote count cannot be negative")

    # Verify tally session exists
    tally_session = session.get(TallySession, session_id)
    if not tally_session:
        raise ValueError(f"TallySession with ID {session_id} not found")

    # Verify party exists
    party = session.get(Party, party_id)
    if not party:
        raise ValueError(f"Party with ID {party_id} not found")

    # Try to get existing tally line
    stmt = select(TallyLine).where(
        TallyLine.tally_session_id == session_id, TallyLine.party_id == party_id
    )
    existing_line = session.exec(stmt).first()

    old_values = None
    if existing_line:
        old_values = {"vote_count": existing_line.vote_count}
        existing_line.vote_count = vote_count
        tally_line = existing_line
    else:
        tally_line = TallyLine(
            tally_session_id=session_id,
            party_id=party_id,
            vote_count=vote_count,
        )

    new_values = {"vote_count": vote_count}

    try:
        session.add(tally_line)
        session.flush()

        # Update total votes in tally session
        total_votes = sum(
            line.vote_count
            for line in session.exec(
                select(TallyLine).where(TallyLine.tally_session_id == session_id)
            ).all()
        )
        tally_session.total_votes_counted = total_votes
        session.add(tally_session)
        session.flush()

        # Create audit log
        audit_log = AuditLog(
            operator_id=tally_session.operator_id,
            action="TALLY_UPDATED",
            entity_type="TallyLine",
            entity_id=tally_line.id,
            old_values=old_values,
            new_values=new_values,
        )
        session.add(audit_log)
        session.flush()

        logger.info(
            f"Updated tally line for party {party_id} in session {session_id}: {vote_count} votes"
        )
        return tally_line

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Failed to update tally line: {e}")
        raise


def get_voter_by_number(
    pen_id: UUID, voter_number: str, session: Session
) -> Voter | None:
    """
    Voter lookup by pen and voter number.

    Args:
        pen_id: UUID of the pen
        voter_number: Voter number within the pen
        session: Database session

    Returns:
        Voter instance if found, None otherwise
    """
    stmt = select(Voter).where(
        Voter.pen_id == pen_id, Voter.voter_number == voter_number
    )
    voter = session.exec(stmt).first()

    if voter:
        logger.debug(f"Found voter {voter_number} in pen {pen_id}")
    else:
        logger.debug(f"Voter {voter_number} not found in pen {pen_id}")

    return voter


def get_pen_voters(
    pen_id: UUID, session: Session, voted_only: bool = False
) -> list[Voter]:
    """
    Get all voters for a pen, optionally filtered by voting status.

    Args:
        pen_id: UUID of the pen
        session: Database session
        voted_only: If True, only return voters who have voted

    Returns:
        List of Voter instances

    Raises:
        ValueError: If pen not found
    """
    # Verify pen exists
    pen = session.get(Pen, pen_id)
    if not pen:
        raise ValueError(f"Pen with ID {pen_id} not found")

    stmt = select(Voter).where(Voter.pen_id == pen_id)
    if voted_only:
        stmt = stmt.where(Voter.has_voted)

    voters = session.exec(stmt).all()
    logger.debug(
        f"Retrieved {len(voters)} voters for pen {pen_id} (voted_only={voted_only})"
    )
    return list(voters)


# ---------------------------------------------------------
# Audit Log Helper
# ---------------------------------------------------------
def create_audit_log(
    session: Session,
    operator_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
) -> AuditLog:
    """
    Create and persist an audit log entry.

    Args:
        session: Database session
        operator_id: UUID of the operator performing the action
        action: Action description (e.g., "VOTER_MARKED", "CONFLICT_RESOLVED")
        entity_type: Type of entity being audited
        entity_id: ID of the entity being audited
        old_values: Previous values (optional)
        new_values: New values (optional)

    Returns:
        Created AuditLog instance
    """
    audit_log = AuditLog(
        operator_id=operator_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
    )
    session.add(audit_log)
    session.flush()

    logger.debug(f"Created audit log: {action} for {entity_type} {entity_id}")
    return audit_log


# ---------------------------------------------------------
# Soft-delete helpers (Sync Spec – Step 3)
# ---------------------------------------------------------
def soft_delete_voter(voter_id: UUID, operator_id: UUID, session: Session) -> None:
    """
    Mark a voter record as deleted (soft delete).

    Args:
        voter_id: UUID of the voter to soft delete
        operator_id: UUID of the operator performing the action
        session: Database session

    Raises:
        ValueError: If voter not found or already deleted
    """
    voter = session.get(Voter, voter_id)
    if not voter:
        raise ValueError(f"Voter with ID {voter_id} not found")

    if voter.deleted_at is not None:
        raise ValueError(f"Voter {voter.voter_number} is already deleted")

    # Store old values for audit
    old_values = {
        "deleted_at": voter.deleted_at,
        "deleted_by": voter.deleted_by,
    }

    # Perform soft delete with actual datetime values
    now = datetime.utcnow()
    voter.deleted_at = now
    voter.deleted_by = operator_id
    voter.updated_at = now

    new_values = {
        "deleted_at": now.isoformat(),
        "deleted_by": str(operator_id),
    }

    try:
        session.add(voter)
        session.flush()

        # Queue for sync
        sync_queue.enqueue_change(
            "Voter", voter_id, ChangeOperation.UPDATE, _entity_to_dict(voter)
        )

        # Create audit log
        audit_log = AuditLog(
            operator_id=operator_id,
            action="VOTER_DELETED",
            entity_type="Voter",
            entity_id=voter_id,
            old_values=old_values,
            new_values=new_values,
        )
        session.add(audit_log)
        session.flush()

        logger.info(f"Soft deleted voter {voter.voter_number} by operator {operator_id}")

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Failed to soft delete voter {voter_id}: {e}")
        raise


def soft_delete_tally_session(ts_id: UUID, operator_id: UUID, session: Session) -> None:
    """
    Soft delete a tally session (admin-only helper).

    Args:
        ts_id: UUID of the tally session to soft delete
        operator_id: UUID of the operator performing the action
        session: Database session

    Raises:
        ValueError: If tally session not found or already deleted
    """
    tally_session = session.get(TallySession, ts_id)
    if not tally_session:
        raise ValueError(f"TallySession with ID {ts_id} not found")

    if tally_session.deleted_at is not None:
        raise ValueError(f"TallySession {tally_session.session_name} is already deleted")

    # Store old values for audit
    old_values = {
        "deleted_at": tally_session.deleted_at,
        "deleted_by": tally_session.deleted_by,
    }

    # Perform soft delete with actual datetime values
    now = datetime.utcnow()
    tally_session.deleted_at = now
    tally_session.deleted_by = operator_id
    tally_session.updated_at = now

    new_values = {
        "deleted_at": now.isoformat(),
        "deleted_by": str(operator_id),
    }

    try:
        session.add(tally_session)
        session.flush()

        # Queue for sync
        sync_queue.enqueue_change(
            "TallySession", ts_id, ChangeOperation.UPDATE, _entity_to_dict(tally_session)
        )

        # Create audit log
        audit_log = AuditLog(
            operator_id=operator_id,
            action="TALLYSESSION_DELETED",
            entity_type="TallySession",
            entity_id=ts_id,
            old_values=old_values,
            new_values=new_values,
        )
        session.add(audit_log)
        session.flush()

        logger.info(f"Soft deleted tally session {tally_session.session_name} by operator {operator_id}")

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Failed to soft delete tally session {ts_id}: {e}")
        raise


def get_active_voters(pen_id: UUID, session: Session) -> list[Voter]:
    """
    Return voters where deleted_at IS NULL.

    Args:
        pen_id: UUID of the pen
        session: Database session

    Returns:
        List of active (non-deleted) Voter instances

    Raises:
        ValueError: If pen not found
    """
    # Verify pen exists
    pen = session.get(Pen, pen_id)
    if not pen:
        raise ValueError(f"Pen with ID {pen_id} not found")

    stmt = select(Voter).where(
        Voter.pen_id == pen_id,
        Voter.deleted_at == None
    )

    voters = session.exec(stmt).all()
    logger.debug(f"Retrieved {len(voters)} active voters for pen {pen_id}")
    return list(voters)
# ---------------------------------------------------------
# Tally Counting DAO helpers (Step 3)
# ---------------------------------------------------------
def get_parties_for_pen(pen_id: UUID, session: Session) -> list[Party]:
    """
    Get all parties available for a pen (Lebanese elections typically have 3 parties).

    Args:
        pen_id: UUID of the pen
        session: Database session

    Returns:
        List of Party instances

    Raises:
        ValueError: If pen not found
    """
    # Verify pen exists
    pen = session.get(Pen, pen_id)
    if not pen:
        raise ValueError(f"Pen with ID {pen_id} not found")

    # For now, return all parties since Lebanese elections are nationwide
    # In future, this could be filtered by region/constituency
    stmt = select(Party)
    parties = session.exec(stmt).all()

    logger.debug(f"Retrieved {len(parties)} parties for pen {pen_id}")
    return list(parties)


def get_candidates_by_party(party_id: UUID, session: Session) -> list[dict[str, Any]]:
    """
    Get candidate list for a party (mock data for now - to be replaced with real candidate model).

    Args:
        party_id: UUID of the party
        session: Database session

    Returns:
        List of candidate dictionaries with id, name, order

    Raises:
        ValueError: If party not found
    """
    # Verify party exists
    party = session.get(Party, party_id)
    if not party:
        raise ValueError(f"Party with ID {party_id} not found")

    # Mock candidate data - in future this will come from a Candidate model
    # Lebanese elections typically have multiple candidates per party
    candidates = [
        {"id": f"{party_id}_candidate_1", "name": f"{party.name} - Candidate 1", "order": 1},
        {"id": f"{party_id}_candidate_2", "name": f"{party.name} - Candidate 2", "order": 2},
        {"id": f"{party_id}_candidate_3", "name": f"{party.name} - Candidate 3", "order": 3},
    ]

    logger.debug(f"Retrieved {len(candidates)} candidates for party {party.name}")
    return candidates


def get_or_create_tally_session(
    pen_id: UUID, operator_id: UUID, session: Session
) -> TallySession:
    """
    Get the active tally session for a pen, or create a new one.
    Lebanese elections maintain one active session per pen.

    Args:
        pen_id: UUID of the pen
        operator_id: UUID of the operator
        session: Database session

    Returns:
        Active TallySession instance

    Raises:
        ValueError: If pen or operator not found
        IntegrityError: If database constraints are violated
    """
    from jcselect.models import User  # Import here to avoid circular imports

    # Verify pen and operator exist
    pen = session.get(Pen, pen_id)
    if not pen:
        raise ValueError(f"Pen with ID {pen_id} not found")

    operator = session.get(User, operator_id)
    if not operator:
        raise ValueError(f"Operator with ID {operator_id} not found")

    # Look for existing active session for this pen
    stmt = select(TallySession).where(
        TallySession.pen_id == pen_id,
        TallySession.completed_at == None,
        TallySession.deleted_at == None
    )
    existing_session = session.exec(stmt).first()

    if existing_session:
        logger.debug(f"Found existing tally session {existing_session.id} for pen {pen_id}")
        return existing_session

    # Create new tally session
    session_name = f"Tally Count - {pen.label}"
    tally_session = TallySession(
        pen_id=pen_id,
        operator_id=operator_id,
        session_name=session_name,
        started_at=datetime.utcnow(),
        ballot_number=0,
    )

    try:
        session.add(tally_session)
        session.flush()

        # Create audit log
        audit_log = AuditLog(
            operator_id=operator_id,
            action="TALLY_SESSION_CREATED",
            entity_type="TallySession",
            entity_id=tally_session.id,
            old_values=None,
            new_values={
                "pen_id": str(pen_id),
                "session_name": session_name,
                "started_at": tally_session.started_at.isoformat(),
            },
        )
        session.add(audit_log)
        session.flush()

        logger.info(f"Created new tally session '{session_name}' for pen {pen_id}")
        return tally_session

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Failed to create tally session for pen {pen_id}: {e}")
        raise


def get_tally_session_counts(session_id: UUID, session: Session) -> dict[str, int]:
    """
    Calculate running totals for a tally session.

    Args:
        session_id: UUID of the tally session
        session: Database session

    Returns:
        Dictionary with vote counts by ballot type

    Raises:
        ValueError: If tally session not found
    """
    # Verify session exists
    tally_session = session.get(TallySession, session_id)
    if not tally_session:
        raise ValueError(f"TallySession with ID {session_id} not found")

    # Get all active tally lines for this session
    stmt = select(TallyLine).where(
        TallyLine.tally_session_id == session_id,
        TallyLine.deleted_at == None
    )
    tally_lines = session.exec(stmt).all()

    # Calculate totals by ballot type
    counts = {
        "total_votes": 0,
        "total_counted": 0,
        "total_candidates": 0,
        "total_white": 0,
        "total_illegal": 0,
        "total_cancel": 0,
        "total_blank": 0,
    }

    for line in tally_lines:
        counts["total_votes"] += line.vote_count
        counts["total_counted"] += line.vote_count

        if line.ballot_type.value == "normal":
            counts["total_candidates"] += line.vote_count
        elif line.ballot_type.value == "white":
            counts["total_white"] += line.vote_count
        elif line.ballot_type.value == "illegal":
            counts["total_illegal"] += line.vote_count
        elif line.ballot_type.value == "cancel":
            counts["total_cancel"] += line.vote_count
        elif line.ballot_type.value == "blank":
            counts["total_blank"] += line.vote_count

    logger.debug(f"Calculated counts for session {session_id}: {counts}")
    return counts
