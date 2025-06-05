"""Sync API routes for push/pull operations."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlmodel import Session, select

from jcselect.api.dependencies import get_db, require_operator_or_admin
from jcselect.api.schemas.sync_schemas import (
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncStatsResponse,
)
from jcselect.dao import create_audit_log
from jcselect.models import (
    Party,
    Pen,
    TallyLine,
    TallySession,
    User,
    Voter,
)
from jcselect.models.sync_schemas import ChangeOperation, EntityChange
from jcselect.sync.queue import sync_queue

router = APIRouter(prefix="/sync", tags=["Synchronization"])


def _validate_entity_dependencies(change: EntityChange, db: Session) -> list[str]:
    """
    Validate that all FK dependencies exist for an entity change.

    Args:
        change: Entity change to validate
        db: Database session

    Returns:
        List of missing dependency names (empty if all valid)
    """
    missing_deps = []

    if change.entity_type == "TallyLine":
        # Check TallySession exists
        session_id = change.data.get("tally_session_id")
        if session_id:
            try:
                session_uuid = UUID(session_id) if isinstance(session_id, str) else session_id
                if not db.get(TallySession, session_uuid):
                    missing_deps.append(f"TallySession({session_id})")
            except (ValueError, TypeError):
                missing_deps.append(f"TallySession({session_id})")

        # Check Party exists
        party_id = change.data.get("party_id")
        if party_id:
            try:
                party_uuid = UUID(party_id) if isinstance(party_id, str) else party_id
                if not db.get(Party, party_uuid):
                    missing_deps.append(f"Party({party_id})")
            except (ValueError, TypeError):
                missing_deps.append(f"Party({party_id})")

    elif change.entity_type == "TallySession":
        # Check Pen exists
        pen_id = change.data.get("pen_id")
        if pen_id:
            try:
                pen_uuid = UUID(pen_id) if isinstance(pen_id, str) else pen_id
                if not db.get(Pen, pen_uuid):
                    missing_deps.append(f"Pen({pen_id})")
            except (ValueError, TypeError):
                missing_deps.append(f"Pen({pen_id})")

        # Check operator exists
        operator_id = change.data.get("operator_id")
        if operator_id:
            try:
                operator_uuid = UUID(operator_id) if isinstance(operator_id, str) else operator_id
                if not db.get(User, operator_uuid):
                    missing_deps.append(f"User({operator_id})")
            except (ValueError, TypeError):
                missing_deps.append(f"User({operator_id})")

    elif change.entity_type == "Voter":
        # Check Pen exists
        pen_id = change.data.get("pen_id")
        if pen_id:
            try:
                pen_uuid = UUID(pen_id) if isinstance(pen_id, str) else pen_id
                if not db.get(Pen, pen_uuid):
                    missing_deps.append(f"Pen({pen_id})")
            except (ValueError, TypeError):
                missing_deps.append(f"Pen({pen_id})")

    return missing_deps


def _apply_entity_change(change: EntityChange, db: Session, operator_id: UUID) -> None:
    """
    Apply a single entity change to the database.

    Args:
        change: Entity change to apply
        db: Database session
        operator_id: ID of the operator making the change
    """
    entity_class_map = {
        "User": User,
        "Voter": Voter,
        "TallySession": TallySession,
        "TallyLine": TallyLine,
        "Party": Party,
        "Pen": Pen,
    }

    entity_class = entity_class_map.get(change.entity_type)
    if not entity_class:
        raise ValueError(f"Unknown entity type: {change.entity_type}")

    # Get existing entity
    entity_id = UUID(change.entity_id) if isinstance(change.entity_id, str) else change.entity_id
    existing_entity = db.get(entity_class, entity_id)

    old_values = {}

    if change.operation == ChangeOperation.DELETE:
        if existing_entity:
            # Soft delete
            old_values = {"deleted_at": existing_entity.deleted_at, "deleted_by": existing_entity.deleted_by}
            existing_entity.deleted_at = datetime.utcnow()
            existing_entity.deleted_by = operator_id
            db.add(existing_entity)

    elif change.operation in (ChangeOperation.CREATE, ChangeOperation.UPDATE):
        if existing_entity:
            # Update existing entity
            for field, value in change.data.items():
                if hasattr(existing_entity, field):
                    old_values[field] = getattr(existing_entity, field)
                    # Convert string UUIDs back to UUID objects
                    if field.endswith("_id") and isinstance(value, str):
                        value = UUID(value)
                    elif field in ("created_at", "updated_at", "deleted_at") and isinstance(value, str):
                        value = datetime.fromisoformat(value)
                    setattr(existing_entity, field, value)
            db.add(existing_entity)
        else:
            # Create new entity
            processed_data = {}
            for field, value in change.data.items():
                # Convert string UUIDs back to UUID objects
                if field.endswith("_id") and isinstance(value, str):
                    processed_data[field] = UUID(value)
                elif field in ("created_at", "updated_at", "deleted_at") and isinstance(value, str):
                    processed_data[field] = datetime.fromisoformat(value)
                else:
                    processed_data[field] = value

            new_entity = entity_class(**processed_data)
            db.add(new_entity)

    # Create audit log
    create_audit_log(
        session=db,
        operator_id=operator_id,
        action=f"SYNC_{change.operation.value.upper()}",
        entity_type=change.entity_type,
        entity_id=entity_id,
        old_values=old_values if old_values else None,
        new_values=change.data
    )


def _check_permissions(user: User, change: EntityChange) -> bool:
    """
    Check if user has permission to make this change.

    Args:
        user: Current user
        change: Entity change to check

    Returns:
        True if user has permission
    """
    # Admins can do everything
    if user.role == "admin":
        return True

    # Operators can only modify certain entities
    if user.role == "operator":
        allowed_entities = ["Voter", "TallySession", "TallyLine"]
        return change.entity_type in allowed_entities

    return False


@router.post("/push", response_model=SyncPushResponse)
async def push_changes(
    push_request: SyncPushRequest,
    current_user: User = Depends(require_operator_or_admin),
    db: Session = Depends(get_db)
) -> SyncPushResponse:
    """
    Process client changes with dependency validation and role-based access control.

    Args:
        push_request: Client changes to process
        current_user: Current authenticated user
        db: Database session

    Returns:
        Push response with processing results
    """
    processed_count = 0
    failed_changes = []
    conflicts = []

    logger.info(f"Processing {len(push_request.changes)} changes from user {current_user.username}")

    for change in push_request.changes:
        try:
            # Check permissions
            if not _check_permissions(current_user, change):
                logger.warning(f"User {current_user.username} lacks permission for {change.entity_type}")
                failed_changes.append(change)
                continue

            # Validate FK dependencies
            missing_deps = _validate_entity_dependencies(change, db)
            if missing_deps:
                logger.warning(f"Missing dependencies for {change.entity_type} {change.entity_id}: {missing_deps}")
                failed_changes.append(change)
                continue

            # Check for conflicts (timestamp-based last-write-wins)
            entity_class_map = {
                "User": User, "Voter": Voter, "TallySession": TallySession,
                "TallyLine": TallyLine, "Party": Party, "Pen": Pen,
            }

            entity_class = entity_class_map.get(change.entity_type)
            if entity_class:
                entity_id = UUID(change.entity_id) if isinstance(change.entity_id, str) else change.entity_id
                existing_entity = db.get(entity_class, entity_id)

                if existing_entity and hasattr(existing_entity, 'updated_at'):
                    server_updated = existing_entity.updated_at
                    client_updated = change.timestamp

                    if server_updated and server_updated > client_updated:
                        logger.info(f"Conflict detected for {change.entity_type} {change.entity_id}: server newer")
                        conflicts.append(change)
                        continue

            # Apply the change
            _apply_entity_change(change, db, current_user.id)
            processed_count += 1

        except Exception as e:
            logger.error(f"Failed to process change {change.entity_id}: {e}")
            failed_changes.append(change)

    # Commit all changes
    try:
        db.commit()
        logger.info(f"Successfully processed {processed_count} changes, {len(failed_changes)} failed, {len(conflicts)} conflicts")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit changes: {e}")
        raise

    return SyncPushResponse(
        processed_count=processed_count,
        failed_changes=failed_changes,
        conflicts=conflicts,
        server_timestamp=datetime.utcnow()
    )


@router.get("/pull", response_model=SyncPullResponse)
async def pull_changes(
    last_sync: datetime | None = Query(None, description="Last sync timestamp"),
    limit: int = Query(100, le=1000, ge=1, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    current_user: User = Depends(require_operator_or_admin),
    db: Session = Depends(get_db)
) -> SyncPullResponse:
    """
    Return paginated server changes since last sync, filtered by user permissions.

    Args:
        last_sync: Last sync timestamp (optional)
        limit: Maximum number of changes to return
        offset: Offset for pagination
        current_user: Current authenticated user
        db: Database session

    Returns:
        Paginated changes response
    """
    changes = []

    # Define entity classes and their access rules
    entity_classes = []
    if current_user.role == "admin":
        # Admins can see everything except AuditLog (per spec)
        entity_classes = [User, Voter, TallySession, TallyLine, Party, Pen]
    else:
        # Operators can only see limited entities
        entity_classes = [Voter, TallySession, TallyLine]

    logger.debug(f"Pulling changes for user {current_user.username} (role: {current_user.role})")

    for entity_class in entity_classes:
        # Build query
        query = select(entity_class)

        # Filter by last_sync timestamp if provided
        if last_sync and hasattr(entity_class, 'updated_at'):
            query = query.where(entity_class.updated_at > last_sync)

        # For operators, filter to their pen only (if entity has pen_id)
        if current_user.role == "operator" and hasattr(entity_class, 'pen_id'):
            # In a real implementation, you'd determine the operator's pen
            # For now, we'll return all changes
            pass

        # Execute query
        results = db.exec(query).all()

        # Convert to EntityChange objects
        for entity in results:
            # Skip soft-deleted entities in the response
            if hasattr(entity, 'deleted_at') and entity.deleted_at is not None:
                continue

            # Convert entity to dict
            entity_data = {}
            for field_name in entity.__class__.model_fields:
                value = getattr(entity, field_name)
                if isinstance(value, datetime):
                    entity_data[field_name] = value.isoformat()
                elif isinstance(value, UUID):
                    entity_data[field_name] = str(value)
                else:
                    entity_data[field_name] = value

            # Determine operation (simplified - assume UPDATE for existing entities)
            operation = ChangeOperation.UPDATE

            change = EntityChange(
                id=entity.id,  # Use entity ID as change ID for simplicity
                entity_type=entity_class.__name__,
                entity_id=entity.id,
                operation=operation,
                data=entity_data,
                timestamp=entity.updated_at if hasattr(entity, 'updated_at') else datetime.utcnow(),
                retry_count=0
            )
            changes.append(change)

    # Sort by timestamp
    changes.sort(key=lambda x: x.timestamp)

    # Apply pagination
    total_available = len(changes)
    paginated_changes = changes[offset:offset + limit]
    has_more = (offset + limit) < total_available

    logger.debug(f"Returning {len(paginated_changes)} changes (total: {total_available}, has_more: {has_more})")

    return SyncPullResponse(
        changes=paginated_changes,
        server_timestamp=datetime.utcnow(),
        has_more=has_more,
        total_available=total_available
    )


@router.get("/stats", response_model=SyncStatsResponse)
async def get_sync_stats(
    current_user: User = Depends(require_operator_or_admin)
) -> SyncStatsResponse:
    """
    Get sync statistics for monitoring.

    Args:
        current_user: Current authenticated user

    Returns:
        Sync statistics
    """
    pending_count = sync_queue.get_pending_count()

    return SyncStatsResponse(
        pending_push_count=pending_count,
        last_successful_sync=None,  # Would be tracked in a real implementation
        sync_enabled=True
    )
