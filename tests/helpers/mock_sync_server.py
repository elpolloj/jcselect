"""Mock sync server for testing."""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from jcselect.models.sync_schemas import (
    EntityChange,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
)


class MockSyncServer:
    """Mock sync server for testing."""

    def __init__(self, port: int = 8999) -> None:
        """Initialize mock server."""
        self.port = port
        self.app = FastAPI(title="Mock Sync Server")
        self.storage: dict[str, dict[str, Any]] = {}  # entity_type -> entity_id -> data
        self.changes_log: list[EntityChange] = []
        self.server_process: Optional[threading.Thread] = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""

        @self.app.post("/sync/push", response_model=SyncPushResponse)
        async def push_changes(request: SyncPushRequest) -> SyncPushResponse:
            """Handle push requests."""
            processed_count = 0
            failed_changes = []
            conflicts = []

            for change in request.changes:
                try:
                    # Validate dependencies (simplified)
                    if self._validate_dependencies(change):
                        # Store the change
                        entity_type = change.entity_type
                        entity_id = str(change.entity_id)

                        if entity_type not in self.storage:
                            self.storage[entity_type] = {}

                        # Check for conflicts (simplified)
                        existing = self.storage[entity_type].get(entity_id)
                        if existing and existing.get("updated_at", "") > change.timestamp.isoformat():
                            conflicts.append(change)
                        else:
                            # Apply the change
                            self.storage[entity_type][entity_id] = change.data
                            self.changes_log.append(change)
                            processed_count += 1
                    else:
                        # Dependency validation failed
                        failed_changes.append(change)

                except Exception:
                    failed_changes.append(change)

            return SyncPushResponse(
                processed_count=processed_count,
                failed_changes=failed_changes,
                conflicts=conflicts,
                server_timestamp=datetime.utcnow()
            )

        @self.app.get("/sync/pull", response_model=SyncPullResponse)
        async def pull_changes(
            last_sync: Optional[datetime] = Query(None),
            limit: int = Query(100, le=1000, ge=1),
            offset: int = Query(0, ge=0)
        ) -> SyncPullResponse:
            """Handle pull requests."""
            # Filter changes by timestamp if provided
            filtered_changes = self.changes_log
            if last_sync:
                filtered_changes = [
                    change for change in self.changes_log
                    if change.timestamp > last_sync
                ]

            # Apply pagination
            total_available = len(filtered_changes)
            paginated_changes = filtered_changes[offset:offset + limit]
            has_more = (offset + limit) < total_available

            return SyncPullResponse(
                changes=paginated_changes,
                server_timestamp=datetime.utcnow(),
                has_more=has_more
            )

        @self.app.get("/health")
        async def health_check() -> dict[str, str]:
            """Health check endpoint."""
            return {"status": "ok"}

    def _validate_dependencies(self, change: EntityChange) -> bool:
        """Simple dependency validation."""
        # For testing, we'll assume all dependencies are valid
        # In a real implementation, this would check FK constraints
        return True

    def start(self) -> None:
        """Start the mock server in a separate thread."""
        if self.server_process and self.server_process.is_alive():
            return

        def run_server() -> None:
            uvicorn.run(self.app, host="127.0.0.1", port=self.port, log_level="critical")

        self.server_process = threading.Thread(target=run_server, daemon=True)
        self.server_process.start()
        
        # Wait a bit for server to start
        time.sleep(1)

    def stop(self) -> None:
        """Stop the mock server."""
        # In a real implementation, we'd properly shutdown uvicorn
        # For testing, the daemon thread will be cleaned up automatically
        pass

    def reset(self) -> None:
        """Reset server state."""
        self.storage.clear()
        self.changes_log.clear()

    def get_entity(self, entity_type: str, entity_id: str) -> Optional[dict[str, Any]]:
        """Get entity data from storage."""
        return self.storage.get(entity_type, {}).get(entity_id)

    def has_change(self, entity_type: str, entity_id: UUID) -> bool:
        """Check if a change exists in the log."""
        return any(
            change.entity_type == entity_type and change.entity_id == entity_id
            for change in self.changes_log
        )


# Global mock server instance for testing
mock_server = MockSyncServer() 