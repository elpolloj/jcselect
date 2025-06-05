"""Sync engine for bidirectional synchronization with cloud server."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from loguru import logger
from PySide6.QtCore import QObject, Signal
from sqlmodel import Session

from jcselect.dao import (
    create_audit_log,
    soft_delete_tally_session,
    soft_delete_voter,
)
from jcselect.models import Pen, TallySession, User, Voter
from jcselect.models.sync_schemas import (
    ChangeOperation,
    EntityChange,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
)
from jcselect.sync.queue import SyncQueue, sync_queue
from jcselect.utils.db import get_session
from jcselect.utils.settings import SyncSettings, sync_settings

# Global sync engine instance for fast access
_sync_engine_instance: SyncEngine | None = None


def get_sync_engine() -> SyncEngine | None:
    """Get the global sync engine instance."""
    return _sync_engine_instance


def set_sync_engine(engine: SyncEngine) -> None:
    """Set the global sync engine instance."""
    global _sync_engine_instance
    _sync_engine_instance = engine


class BackoffStrategy:
    """Handles exponential backoff calculation for sync retries."""

    def __init__(self, base: float = 2.0, max_delay: float = 300.0) -> None:
        """
        Initialize backoff strategy.

        Args:
            base: Base multiplier for exponential backoff
            max_delay: Maximum delay in seconds
        """
        self.base = base
        self.max_delay = max_delay

    def calculate_delay(self, retry_count: int) -> float:
        """
        Calculate delay for the given retry attempt.

        Args:
            retry_count: Number of previous retry attempts

        Returns:
            Delay in seconds, capped at max_delay
        """
        delay = self.base ** retry_count
        return min(delay, self.max_delay)


class SyncEngine(QObject):
    """Core sync engine for bidirectional synchronization with Qt signal support."""

    # Qt signals for real-time sync notifications
    syncCompleted = Signal()
    syncStarted = Signal() 
    syncFailed = Signal(str)  # error_message
    tallyLineUpdated = Signal(str)  # tally_line_id
    tallySessionUpdated = Signal(str)  # tally_session_id
    entityUpdated = Signal(str, str)  # entity_type, entity_id

    def __init__(self, settings: SyncSettings, queue: SyncQueue) -> None:
        """
        Initialize sync engine.

        Args:
            settings: Sync configuration settings
            queue: Sync queue for managing changes
        """
        super().__init__()
        self.settings = settings
        self.queue = queue
        self.backoff = BackoffStrategy(
            base=settings.sync_backoff_base,
            max_delay=settings.sync_backoff_max_seconds
        )
        self._client: httpx.AsyncClient | None = None
        self._running = False
        self._sync_task: asyncio.Task[None] | None = None
        self._last_sync_timestamp: datetime | None = None

        # Fast sync state
        self._fast_sync_pending = False

        # Register this instance globally
        set_sync_engine(self)

    async def trigger_fast_sync(self) -> None:
        """
        Trigger immediate sync cycle for fast updates.
        Used when critical changes occur that need immediate propagation.
        Implements debounced behavior to avoid excessive sync calls.
        """
        if self._fast_sync_pending:
            logger.debug("Fast sync already pending, skipping")
            return
            
        if not self._running:
            logger.warning("Cannot trigger fast sync: engine not running")
            return
            
        self._fast_sync_pending = True
        logger.debug("Fast sync triggered")
        
        try:
            # Schedule sync with small delay for debouncing (250ms as per spec)
            await asyncio.sleep(0.25)
            await self.sync_cycle()
        except Exception as e:
            logger.error(f"Fast sync failed: {e}")
        finally:
            self._fast_sync_pending = False

    async def start(self) -> None:
        """Start the sync engine with periodic sync cycles."""
        if self._running:
            logger.warning("Sync engine is already running")
            return

        self._running = True
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Content-Type": "application/json"}
        )

        logger.info("Sync engine started")

        # Start periodic sync cycle
        self._sync_task = asyncio.create_task(self._periodic_sync())

    async def stop(self) -> None:
        """Stop the sync engine and cleanup resources."""
        if not self._running:
            return

        self._running = False

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        if self._client:
            await self._client.aclose()
            self._client = None

        logger.info("Sync engine stopped")

    async def _periodic_sync(self) -> None:
        """Run periodic sync cycles."""
        while self._running:
            try:
                await self.sync_cycle()
            except Exception as e:
                logger.error(f"Sync cycle failed: {e}")
                self.syncFailed.emit(str(e))

            # Wait for next sync interval
            await asyncio.sleep(self.settings.sync_interval_seconds)

    async def sync_cycle(self) -> None:
        """
        Perform a complete sync cycle: push local changes, then pull remote changes.
        """
        if not self._client:
            logger.error("Sync engine not started")
            return

        logger.debug("Starting sync cycle")
        self.syncStarted.emit()

        try:
            # Push local changes first
            await self.push_changes()

            # Then pull remote changes
            await self.pull_changes_paginated()

            logger.debug("Sync cycle completed successfully")
            self.syncCompleted.emit()

        except Exception as e:
            logger.error(f"Sync cycle failed: {e}")
            self.syncFailed.emit(str(e))
            raise

    async def push_changes(self) -> None:
        """
        Push local changes to server in dependency order.
        """
        if not self._client:
            raise RuntimeError("Sync engine not started")

        # Get pending changes in dependency order
        pending_changes = self.queue.get_pending_changes_ordered(limit=100)

        if not pending_changes:
            logger.debug("No pending changes to push")
            return

        logger.info(f"Pushing {len(pending_changes)} changes to server")

        # Group changes into batches respecting payload size limit
        batches = self._create_batches(pending_changes)

        for batch in batches:
            await self._push_batch(batch)

    def _create_batches(self, changes: list[EntityChange]) -> list[list[EntityChange]]:
        """
        Create batches of changes respecting payload size limits and dependency order.

        Args:
            changes: List of changes in dependency order

        Returns:
            List of batches, each containing changes
        """
        batches = []
        current_batch = []
        current_size = 0

        for change in changes:
            # Estimate serialized size (rough approximation)
            change_size = len(json.dumps(change.model_dump()).encode('utf-8'))

            # Start new batch if adding this change would exceed limit
            if (current_size + change_size > self.settings.max_payload_size and
                    len(current_batch) > 0):
                batches.append(current_batch)
                current_batch = []
                current_size = 0

            current_batch.append(change)
            current_size += change_size

        # Add remaining changes as final batch
        if current_batch:
            batches.append(current_batch)

        return batches

    async def _push_batch(self, batch: list[EntityChange]) -> None:
        """
        Push a single batch of changes to the server.

        Args:
            batch: List of changes to push
        """
        if not self._client:
            raise RuntimeError("Sync engine not started")

        request = SyncPushRequest(
            changes=batch,
            client_timestamp=datetime.utcnow()
        )

        try:
            response = await self._client.post(
                f"{self.settings.sync_api_url}/sync/push",
                json=request.model_dump(mode="json")
            )

            if response.status_code == 200:
                push_response = SyncPushResponse(**response.json())
                await self._handle_push_response(push_response, batch)
            elif response.status_code == 409:
                # Dependency conflicts
                logger.warning(f"Dependency conflicts in batch of {len(batch)} changes")
                for change in batch:
                    self.queue.handle_dependency_conflict(str(change.id), "Missing FK dependency")
            else:
                # Other errors
                error_msg = f"Server error {response.status_code}: {response.text}"
                logger.error(error_msg)
                for change in batch:
                    self.queue.mark_failed(str(change.id), error_msg, change.retry_count + 1)

        except Exception as e:
            error_msg = f"Network error: {e}"
            logger.error(error_msg)
            for change in batch:
                self.queue.mark_failed(str(change.id), error_msg, change.retry_count + 1)

    async def _handle_push_response(
        self,
        response: SyncPushResponse,
        batch: list[EntityChange]
    ) -> None:
        """
        Handle server response to push request.

        Args:
            response: Server response
            batch: Original batch of changes
        """
        # Mark successfully processed changes as synced
        successful_ids = []
        failed_changes = {change.entity_id for change in response.failed_changes}
        conflict_changes = {change.entity_id for change in response.conflicts}

        for change in batch:
            if change.entity_id not in failed_changes and change.entity_id not in conflict_changes:
                successful_ids.append(str(change.id))

        if successful_ids:
            self.queue.mark_synced(successful_ids)
            logger.debug(f"Marked {len(successful_ids)} changes as synced")

        # Handle failed changes
        for failed_change in response.failed_changes:
            original_change = next(
                (c for c in batch if c.entity_id == failed_change.entity_id),
                None
            )
            if original_change:
                self.queue.mark_failed(
                    str(original_change.id),
                    "Server processing failed",
                    original_change.retry_count + 1
                )

        # Handle conflicts (server version is newer)
        for conflict_change in response.conflicts:
            original_change = next(
                (c for c in batch if c.entity_id == conflict_change.entity_id),
                None
            )
            if original_change:
                # For conflicts, we apply the server version and remove local change
                await self._apply_remote_change(conflict_change)
                self.queue.mark_synced([str(original_change.id)])
                logger.info(f"Resolved conflict for {conflict_change.entity_type} {conflict_change.entity_id}")

    async def pull_changes_paginated(self) -> None:
        """
        Pull changes from server with pagination support.
        """
        if not self._client:
            raise RuntimeError("Sync engine not started")

        logger.debug("Pulling changes from server")

        all_changes: list[EntityChange] = []
        offset = 0
        pages_fetched = 0

        while pages_fetched < self.settings.sync_max_pull_pages:
            try:
                params: dict[str, str | int] = {
                    "limit": self.settings.sync_pull_page_size,
                    "offset": offset
                }

                if self._last_sync_timestamp:
                    params["last_sync"] = self._last_sync_timestamp.isoformat()

                response = await self._client.get(
                    f"{self.settings.sync_api_url}/sync/pull",
                    params=params
                )

                if response.status_code != 200:
                    logger.error(f"Pull failed with status {response.status_code}: {response.text}")
                    break

                pull_response = SyncPullResponse(**response.json())
                all_changes.extend(pull_response.changes)

                logger.debug(f"Fetched page {pages_fetched + 1} with {len(pull_response.changes)} changes")

                # Update sync timestamp
                self._last_sync_timestamp = pull_response.server_timestamp

                # Check if we have more pages
                if not pull_response.has_more:
                    break

                offset += self.settings.sync_pull_page_size
                pages_fetched += 1

            except Exception as e:
                logger.error(f"Error during pull: {e}")
                break

        if all_changes:
            await self.apply_remote_changes(all_changes)
            logger.info(f"Applied {len(all_changes)} remote changes")

    async def apply_remote_changes(self, changes: list[EntityChange]) -> None:
        """
        Apply remote changes to local database.

        Args:
            changes: List of remote changes to apply
        """
        for change in changes:
            try:
                await self._apply_remote_change(change)
            except Exception as e:
                logger.error(f"Failed to apply remote change {change.id}: {e}")

    async def _apply_remote_change(self, change: EntityChange) -> None:
        """
        Apply a single remote change to local database.

        Args:
            change: Remote change to apply
        """
        with get_session() as session:
            try:
                if change.operation == ChangeOperation.DELETE:
                    await self._handle_remote_delete(change, session)
                elif change.operation in (ChangeOperation.CREATE, ChangeOperation.UPDATE):
                    await self._handle_remote_upsert(change, session)

                session.commit()
                logger.debug(f"Applied {change.operation} for {change.entity_type} {change.entity_id}")
                
                # Emit specific signals for real-time updates
                self._emit_entity_signals(change)

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to apply change {change.id}: {e}")
                raise

    def _emit_entity_signals(self, change: EntityChange) -> None:
        """Emit specific Qt signals based on entity type for real-time updates."""
        entity_type = change.entity_type
        entity_id = str(change.entity_id)
        
        # Emit general entity update signal
        self.entityUpdated.emit(entity_type, entity_id)
        
        # Emit specific signals for tally-related entities that results controller cares about
        if entity_type == "TallyLine":
            self.tallyLineUpdated.emit(entity_id)
            logger.debug(f"Emitted tallyLineUpdated signal for {entity_id}")
        elif entity_type == "TallySession":
            self.tallySessionUpdated.emit(entity_id)
            logger.debug(f"Emitted tallySessionUpdated signal for {entity_id}")
        
        logger.debug(f"Emitted entityUpdated signal for {entity_type} {entity_id}")

    async def _handle_remote_delete(self, change: EntityChange, session: Session) -> None:
        """Handle remote delete operations (soft delete)."""
        entity_id = change.entity_id
        deleted_by = change.data.get("deleted_by")

        if change.entity_type == "Voter":
            # Use soft delete function
            if deleted_by:
                soft_delete_voter(entity_id, UUID(deleted_by), session)
        elif change.entity_type == "TallySession":
            if deleted_by:
                soft_delete_tally_session(entity_id, UUID(deleted_by), session)
        else:
            logger.warning(f"Remote delete not implemented for {change.entity_type}")

    async def _handle_remote_upsert(self, change: EntityChange, session: Session) -> None:
        """Handle remote create/update operations."""
        entity_type = change.entity_type
        entity_id = change.entity_id
        data = change.data

        # Check for conflicts with local version
        existing_entity = None
        entity_class = self._get_entity_class(entity_type)

        if entity_class:
            existing_entity = session.get(entity_class, entity_id)

        if existing_entity:
            # Resolve conflicts using last-write-wins
            await self._resolve_conflict(existing_entity, change, session)
        else:
            # Create new entity
            await self._create_entity(entity_type, data, session)

    def _get_entity_class(self, entity_type: str) -> type | None:
        """Get SQLModel class for entity type."""
        entity_map = {
            "User": User,
            "Voter": Voter,
            "TallySession": TallySession,
            "Pen": Pen,
            # Add more as needed
        }
        return entity_map.get(entity_type)

    async def _resolve_conflict(
        self,
        local_entity: Any,
        remote_change: EntityChange,
        session: Session
    ) -> None:
        """
        Resolve conflicts using last-write-wins strategy.

        Args:
            local_entity: Local entity
            remote_change: Remote change
            session: Database session
        """
        local_updated = getattr(local_entity, "updated_at", None)
        remote_updated = remote_change.timestamp

        if local_updated is None or remote_updated > local_updated:
            # Remote wins - update local entity
            old_values = {}
            new_values = {}

            for field, value in remote_change.data.items():
                if hasattr(local_entity, field):
                    old_values[field] = getattr(local_entity, field)
                    setattr(local_entity, field, value)
                    new_values[field] = value

            # Log conflict resolution
            create_audit_log(
                session=session,
                operator_id=UUID("00000000-0000-0000-0000-000000000000"),  # System user
                action="CONFLICT_RESOLVED",
                entity_type=remote_change.entity_type,
                entity_id=remote_change.entity_id,
                old_values=old_values,
                new_values=new_values
            )

            logger.info(
                f"Conflict resolved: remote wins for {remote_change.entity_type} {remote_change.entity_id}"
            )
        else:
            # Local wins - no action needed
            logger.info(
                f"Conflict resolved: local wins for {remote_change.entity_type} {remote_change.entity_id}"
            )

    async def _create_entity(self, entity_type: str, data: dict[str, Any], session: Session) -> None:
        """Create a new entity from remote data."""
        entity_class = self._get_entity_class(entity_type)

        if not entity_class:
            logger.warning(f"Unknown entity type: {entity_type}")
            return

        try:
            # Convert string UUIDs back to UUID objects
            processed_data = {}
            for key, value in data.items():
                if key.endswith("_id") and isinstance(value, str):
                    processed_data[key] = UUID(value)
                elif key in ("created_at", "updated_at", "deleted_at") and isinstance(value, str):
                    processed_data[key] = datetime.fromisoformat(value)
                else:
                    processed_data[key] = value

            entity = entity_class(**processed_data)
            session.add(entity)
            logger.debug(f"Created new {entity_type} from remote data")

        except Exception as e:
            logger.error(f"Failed to create {entity_type}: {e}")
            raise


# Global sync engine instance
sync_engine = SyncEngine(sync_settings, sync_queue)
