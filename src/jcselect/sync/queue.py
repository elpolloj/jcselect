"""Sync queue for managing local changes before synchronization."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from types import TracebackType
from typing import Any, Optional
from uuid import UUID, uuid4

from loguru import logger

from jcselect.models.sync_schemas import ChangeOperation, EntityChange
from jcselect.utils.settings import sync_settings


class SyncQueue:
    """SQLite-backed queue for managing changes to be synchronized with the server."""

    def __init__(self, db_path: Path) -> None:
        """
        Initialize the sync queue with SQLite persistence.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
        logger.debug(f"SyncQueue initialized with database at {db_path}")

    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _init_database(self) -> None:
        """Initialize the SQLite database and create tables if needed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    next_retry_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_queue_entity_type ON sync_queue(entity_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_queue_next_retry ON sync_queue(next_retry_at)")

            conn.commit()

    def enqueue_change(
        self,
        entity_type: str,
        entity_id: UUID,
        operation: ChangeOperation,
        data: dict[str, Any]
    ) -> EntityChange:
        """
        Add a change to the sync queue.

        Args:
            entity_type: Type of entity (e.g., 'Voter', 'TallySession')
            entity_id: ID of the changed entity
            operation: Type of change operation
            data: Entity data dictionary

        Returns:
            The created EntityChange
        """
        change_id = uuid4()
        timestamp = datetime.utcnow()

        change = EntityChange(
            id=change_id,
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            data=data,
            timestamp=timestamp,
            retry_count=0
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sync_queue (
                    id, entity_type, entity_id, operation, data, timestamp, status, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(change_id),
                entity_type,
                str(entity_id),
                operation.value,
                json.dumps(data),
                timestamp.isoformat(),
                'pending',
                0
            ))
            conn.commit()

        logger.debug(
            f"Enqueued {operation} change for {entity_type} {entity_id}: {change_id}"
        )

        # Check for immediate sync trigger for TallyLine changes
        if entity_type == "TallyLine" and self._should_trigger_fast_sync():
            self._trigger_fast_sync_async()

        return change

    def enqueue_tally_line(self, line: TallyLine, operation: ChangeOperation) -> EntityChange:
        """
        Enqueue a TallyLine change with automatic serialization.

        Args:
            line: TallyLine entity to enqueue
            operation: Type of change operation (CREATE, UPDATE, DELETE)

        Returns:
            The created EntityChange
        """
        from jcselect.dao import tally_line_to_dict

        # Serialize TallyLine using the existing helper
        data = tally_line_to_dict(line)

        # Enqueue the change
        return self.enqueue_change("TallyLine", line.id, operation, data)

    def trigger_fast_sync(self) -> None:
        """
        Trigger an immediate fast sync cycle if sync engine is available.
        This method is safe to call from any thread.
        """
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule the fast sync as a task
                asyncio.create_task(self._fast_sync_cycle())
            else:
                logger.debug("No running event loop for fast sync")
        except RuntimeError:
            # No event loop running, try to trigger via callback
            self._trigger_fast_sync_async()

    def _should_trigger_fast_sync(self) -> bool:
        """Check if fast sync should be triggered for TallyLine changes."""
        from jcselect.utils.settings import sync_settings
        return sync_settings.sync_enabled and sync_settings.sync_fast_tally_enabled

    def _trigger_fast_sync_async(self) -> None:
        """Trigger fast sync asynchronously if possible."""
        try:
            # Import here to avoid circular imports
            from jcselect.sync.engine import get_sync_engine

            engine = get_sync_engine()
            if engine and hasattr(engine, 'trigger_fast_sync'):
                # Create a background task for fast sync
                import asyncio
                asyncio.create_task(engine.trigger_fast_sync())
                logger.debug("Fast sync triggered for TallyLine changes")
        except Exception as e:
            logger.debug(f"Could not trigger fast sync: {e}")

    async def _fast_sync_cycle(self) -> None:
        """Perform a fast sync cycle focusing on TallyLine changes."""
        try:
            from jcselect.sync.engine import get_sync_engine

            engine = get_sync_engine()
            if engine:
                await engine.sync_cycle()
        except Exception as e:
            logger.error(f"Fast sync cycle failed: {e}")

    def get_pending_changes_ordered(self, limit: int = 100) -> list[EntityChange]:
        """
        Get pending changes in dependency order.

        Args:
            limit: Maximum number of changes to return

        Returns:
            List of pending changes ordered by entity dependency
        """
        entity_order = sync_settings.sync_entity_order
        all_changes: list[EntityChange] = []
        remaining_limit = limit

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            for entity_type in entity_order:
                if remaining_limit <= 0:
                    break

                changes = self._get_pending_by_type(conn, entity_type, remaining_limit)
                all_changes.extend(changes)
                remaining_limit -= len(changes)

        logger.debug(f"Retrieved {len(all_changes)} pending changes in dependency order")
        return all_changes

    def _get_pending_by_type(
        self,
        conn: sqlite3.Connection,
        entity_type: str,
        limit: int
    ) -> list[EntityChange]:
        """Get pending changes for a specific entity type."""
        cursor = conn.execute("""
            SELECT id, entity_type, entity_id, operation, data, timestamp, retry_count
            FROM sync_queue
            WHERE entity_type = ? AND status = 'pending'
            ORDER BY timestamp ASC
            LIMIT ?
        """, (entity_type, limit))

        changes = []
        for row in cursor:
            changes.append(EntityChange(
                id=UUID(row['id']),
                entity_type=row['entity_type'],
                entity_id=UUID(row['entity_id']),
                operation=ChangeOperation(row['operation']),
                data=json.loads(row['data']),
                timestamp=datetime.fromisoformat(row['timestamp']),
                retry_count=row['retry_count']
            ))

        return changes

    def get_retry_ready_changes(self) -> list[EntityChange]:
        """
        Get changes that are ready for retry based on their next_retry_at timestamp.

        Returns:
            List of changes ready for retry
        """
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute("""
                SELECT id, entity_type, entity_id, operation, data, timestamp, retry_count
                FROM sync_queue
                WHERE status = 'retry' AND next_retry_at <= ?
                ORDER BY next_retry_at ASC
            """, (now,))

            changes = []
            for row in cursor:
                changes.append(EntityChange(
                    id=UUID(row['id']),
                    entity_type=row['entity_type'],
                    entity_id=UUID(row['entity_id']),
                    operation=ChangeOperation(row['operation']),
                    data=json.loads(row['data']),
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    retry_count=row['retry_count']
                ))

        logger.debug(f"Retrieved {len(changes)} retry-ready changes")
        return changes

    def mark_synced(self, change_ids: list[str]) -> None:
        """
        Mark changes as successfully synced and remove them from the queue.

        Args:
            change_ids: List of change IDs to mark as synced
        """
        if not change_ids:
            return

        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join('?' * len(change_ids))
            conn.execute(f"""
                DELETE FROM sync_queue
                WHERE id IN ({placeholders})
            """, change_ids)
            conn.commit()

        logger.debug(f"Marked {len(change_ids)} changes as synced and removed from queue")

    def mark_failed(self, change_id: str, error: str, retry_count: int) -> None:
        """
        Mark a change as failed and schedule it for retry.

        Args:
            change_id: ID of the failed change
            error: Error message describing the failure
            retry_count: Current retry count
        """
        max_retries = sync_settings.sync_max_retries

        if retry_count >= max_retries:
            # Max retries exceeded, mark as permanently failed
            status = 'failed_permanent'
            next_retry_at = None
            logger.warning(f"Change {change_id} permanently failed after {retry_count} retries: {error}")
        else:
            # Schedule for retry with exponential backoff
            status = 'retry'
            next_retry_at = self._calculate_next_retry(retry_count)
            logger.debug(f"Change {change_id} scheduled for retry at {next_retry_at}: {error}")

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sync_queue
                SET status = ?, retry_count = ?, last_error = ?, next_retry_at = ?
                WHERE id = ?
            """, (
                status,
                retry_count,
                error,
                next_retry_at.isoformat() if next_retry_at else None,
                change_id
            ))
            conn.commit()

    def handle_dependency_conflict(self, change_id: str, missing_fk: str) -> None:
        """
        Mark change for retry due to missing FK dependency.

        Args:
            change_id: ID of the change with dependency conflict
            missing_fk: Description of the missing foreign key
        """
        next_retry_at = datetime.utcnow() + timedelta(minutes=5)
        error_msg = f"Missing FK: {missing_fk}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sync_queue
                SET status = 'dependency_conflict', last_error = ?, next_retry_at = ?
                WHERE id = ?
            """, (error_msg, next_retry_at.isoformat(), change_id))
            conn.commit()

        logger.debug(f"Change {change_id} marked for dependency conflict retry: {error_msg}")

    def _calculate_next_retry(self, retry_count: int) -> datetime:
        """
        Calculate the next retry time using exponential backoff.

        Args:
            retry_count: Current retry count

        Returns:
            Datetime when the next retry should occur
        """
        base = sync_settings.sync_backoff_base
        max_seconds = sync_settings.sync_backoff_max_seconds

        # Exponential backoff: base^retry_count seconds, capped at max_seconds
        backoff_seconds = min(base ** retry_count, max_seconds)

        return datetime.utcnow() + timedelta(seconds=backoff_seconds)

    def get_queue_size(self) -> int:
        """Get the current queue size (all statuses)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sync_queue")
            result = cursor.fetchone()
            return int(result[0]) if result else 0

    def get_pending_count(self) -> int:
        """Get the count of pending changes."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sync_queue WHERE status = 'pending'")
            result = cursor.fetchone()
            return int(result[0]) if result else 0

    def get_retry_count(self) -> int:
        """Get the count of changes scheduled for retry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sync_queue WHERE status = 'retry'")
            result = cursor.fetchone()
            return int(result[0]) if result else 0

    def get_failed_count(self) -> int:
        """Get the count of permanently failed changes."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sync_queue WHERE status = 'failed_permanent'")
            result = cursor.fetchone()
            return int(result[0]) if result else 0

    def clear(self) -> None:
        """Clear all items from the queue (useful for testing)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sync_queue")
            conn.commit()

        logger.debug("Cleared all items from sync queue")

    def close(self) -> None:
        """Close any open database connections (useful for tests on Windows)."""
        # SQLite connections are auto-closed when out of scope,
        # but we can force cleanup for test environments
        import gc
        gc.collect()

    def __enter__(self) -> SyncQueue:
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type: Optional[type[Exception]], exc_val: Exception, exc_tb: TracebackType) -> None:
        """Clean up resources when exiting context."""
        self.close()


# Global sync queue instance
sync_queue = SyncQueue(Path.home() / ".jcselect" / "sync_queue.db")
