# JCSELECT Sync Engine & Cloud API - Technical Specification (Revised)

## 1. Overview

Build an offline-first synchronization system that enables jcselect desktop clients to push local changes (voters marked as voted, tally sessions, audit logs) to a VPS-hosted MSSQL database and pull remote changes back to local SQLite storage. The system implements "eventually consistent" bidirectional sync with entity-level "last write wins" conflict resolution and soft-delete tombstone handling.

## 2. Technical Requirements

### 2.1 Sync Architecture
- **Granularity**: Entity-level sync with whole record updates
- **Conflict Resolution**: Last write wins based on `updated_at` timestamps
- **Deletion Strategy**: Soft deletes with `deleted_at` and `deleted_by` tombstone fields
- **Dependency Handling**: Dependency-ordered batching (parents before children)
- **Pagination**: Server-side cursor pagination for large pull responses
- **Transport**: HTTPS with JWT authentication

### 2.2 Soft Delete Implementation
**All syncable entities get these fields**:
```sql
deleted_at TIMESTAMP NULL
deleted_by UUID NULL  -- references users.id
```

**Delete behavior**:
- Physical DELETE → UPDATE SET deleted_at=NOW(), deleted_by=operator_id
- Sync treats as normal UPDATE operation
- UI filters out deleted_at IS NOT NULL records

### 2.3 Batch Dependency Ordering
**Push order**: Parent entities before children
```
1. User, Party, Pen (reference data)
2. TallySession
3. Voter, TallyLine
4. AuditLog (last)
```

**Conflict handling**: 409 status for missing FK dependencies, client retries next cycle

### 2.4 Pull Pagination
- Server implements cursor-based pagination with `has_more` flag
- Client requests: `GET /sync/pull?last_sync=2024-01-01T10:00:00Z&limit=100&offset=0`
- Server response includes `has_more: true` if additional pages exist

## 3. Architecture Design

### 3.1 Enhanced Data Flow
```
Local Change → Soft Delete Check → Dependency Sort → Batch → Server
     ↓              ↓                   ↓           ↓        ↓
  Queue Item    Tombstone Set      Parent First   Chunked   FK Validation
                                                            + 409 Handling
```

### 3.2 Conflict Resolution Flow
```
Client Entity (updated_at: T1) ←→ Server Entity (updated_at: T2)
                ↓
         Compare Timestamps
                ↓
    T2 > T1: Server Wins (Client overwrites local)
    T1 > T2: Client Wins (Server accepts push)
    T1 = T2: No conflict (identical timestamps)
                ↓
         Log to AuditLog
```

## 4. Detailed Implementation Plan

### Step 1: Database Schema Updates for Soft Deletes

**Alembic Migration**: Add soft delete fields to all syncable entities

```sql
-- Add soft delete columns to all syncable tables
ALTER TABLE voters ADD COLUMN deleted_at TIMESTAMP NULL;
ALTER TABLE voters ADD COLUMN deleted_by UUID NULL;
ALTER TABLE tally_sessions ADD COLUMN deleted_at TIMESTAMP NULL;
ALTER TABLE tally_sessions ADD COLUMN deleted_by UUID NULL;
ALTER TABLE tally_lines ADD COLUMN deleted_at TIMESTAMP NULL;
ALTER TABLE tally_lines ADD COLUMN deleted_by UUID NULL;
ALTER TABLE audit_log ADD COLUMN deleted_at TIMESTAMP NULL;
ALTER TABLE audit_log ADD COLUMN deleted_by UUID NULL;
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP NULL;
ALTER TABLE users ADD COLUMN deleted_by UUID NULL;
ALTER TABLE parties ADD COLUMN deleted_at TIMESTAMP NULL;
ALTER TABLE parties ADD COLUMN deleted_by UUID NULL;

-- Add foreign key constraints for deleted_by
ALTER TABLE voters ADD CONSTRAINT fk_voters_deleted_by 
    FOREIGN KEY (deleted_by) REFERENCES users(id);
-- (repeat for all tables)

-- Add indexes for soft delete queries
CREATE INDEX idx_voters_deleted_at ON voters(deleted_at);
CREATE INDEX idx_tally_sessions_deleted_at ON tally_sessions(deleted_at);
-- (repeat for all tables)
```

### Step 2: Enhanced Settings Configuration

**File**: `src/JCSELECT/utils/settings.py`

```python
class SyncSettings(BaseSettings):
    """Enhanced sync configuration"""
    
    # Core sync settings
    sync_api_url: HttpUrl
    sync_jwt_secret: str = Field(min_length=32)
    sync_interval_seconds: int = Field(ge=60, le=3600, default=300)
    sync_max_payload_size: int = Field(ge=1024, le=10485760, default=1048576)
    sync_enabled: bool = True
    
    # Pagination settings
    sync_pull_page_size: int = Field(ge=10, le=1000, default=100)
    sync_max_pull_pages: int = Field(ge=1, le=100, default=10)
    
    # Retry and backoff
    sync_max_retries: int = Field(ge=1, le=10, default=5)
    sync_backoff_base: float = Field(ge=1.0, le=5.0, default=2.0)
    sync_backoff_max_seconds: int = Field(ge=60, le=1800, default=300)
    
    # Dependency ordering
    sync_entity_order: List[str] = [
        "User", "Party", "Pen", 
        "TallySession", 
        "Voter", "TallyLine", 
        "AuditLog"
    ]
```

### Step 3: Soft Delete DAO Integration

**File**: `src/JCSELECT/dao.py` (modifications)

```python
def soft_delete_voter(voter_id: str, operator_id: str, session: Session) -> None:
    """Soft delete voter and queue for sync"""
    voter = session.get(Voter, voter_id)
    if not voter or voter.deleted_at is not None:
        raise ValueError("Voter not found or already deleted")
    
    voter.deleted_at = func.now()
    voter.deleted_by = operator_id
    voter.updated_at = func.now()
    
    # Queue for sync
    sync_queue.enqueue_change("Voter", voter_id, ChangeOperation.UPDATE, 
                             voter_to_dict(voter))
    
    # Audit log
    audit_entry = AuditLog(
        operator_id=operator_id,
        action="VOTER_DELETED",
        entity_type="Voter",
        entity_id=voter_id,
        new_values={"deleted_at": voter.deleted_at, "deleted_by": operator_id}
    )
    session.add(audit_entry)

def get_active_voters(pen_id: str, session: Session) -> List[Voter]:
    """Get non-deleted voters for a pen"""
    return session.query(Voter).filter(
        Voter.pen_id == pen_id,
        Voter.deleted_at.is_(None)
    ).all()
```

### Step 4: Dependency-Ordered Sync Queue

**File**: `src/JCSELECT/sync/queue.py`

```python
class SyncQueue:
    """Enhanced queue with dependency ordering"""
    
    def get_pending_changes_ordered(self, limit: int = 100) -> List[EntityChange]:
        """Get pending changes in dependency order"""
        entity_order = self.settings.sync_entity_order
        all_changes = []
        
        for entity_type in entity_order:
            changes = self._get_pending_by_type(entity_type, limit)
            all_changes.extend(changes)
            limit -= len(changes)
            if limit <= 0:
                break
        
        return all_changes
    
    def handle_dependency_conflict(self, change_id: str, missing_fk: str) -> None:
        """Mark change for retry due to missing FK dependency"""
        self._update_queue_item(
            change_id,
            status='dependency_conflict',
            last_error=f'Missing FK: {missing_fk}',
            next_retry_at=datetime.utcnow() + timedelta(minutes=5)
        )
```

### Step 5: Enhanced Sync Engine with Dependency Handling

**File**: `src/JCSELECT/sync/engine.py`

```python
class SyncEngine:
    """Enhanced sync engine with dependency handling"""
    
    async def push_changes(self) -> PushResult:
        """Push changes in dependency order with conflict handling"""
        pending_changes = self.queue.get_pending_changes_ordered()
        
        for batch in self._create_dependency_batches(pending_changes):
            try:
                response = await self._push_batch(batch)
                self._handle_push_response(response, batch)
            except DependencyConflictError as e:
                self._handle_dependency_conflicts(e.failed_changes)
            except Exception as e:
                self._handle_batch_failure(batch, str(e))
    
    def _create_dependency_batches(self, changes: List[EntityChange]) -> List[List[EntityChange]]:
        """Group changes by entity type maintaining dependency order"""
        batches = []
        current_batch = []
        current_entity_type = None
        
        for change in changes:
            if change.entity_type != current_entity_type:
                if current_batch:
                    batches.append(current_batch)
                current_batch = [change]
                current_entity_type = change.entity_type
            else:
                current_batch.append(change)
                
                # Split if batch too large
                if self._calculate_batch_size(current_batch) > self.settings.sync_max_payload_size:
                    batches.append(current_batch[:-1])
                    current_batch = [change]
        
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    async def pull_changes_paginated(self) -> PullResult:
        """Pull changes with pagination support"""
        all_changes = []
        offset = 0
        
        while True:
            response = await self.api_client.get(
                f"/sync/pull",
                params={
                    "last_sync": self.last_sync_timestamp.isoformat(),
                    "limit": self.settings.sync_pull_page_size,
                    "offset": offset
                }
            )
            
            pull_data = SyncPullResponse(**response.json())
            all_changes.extend(pull_data.changes)
            
            if not pull_data.has_more:
                break
                
            offset += self.settings.sync_pull_page_size
            
            # Safety limit
            if offset > self.settings.sync_max_pull_pages * self.settings.sync_pull_page_size:
                logger.warning("Reached max pull pages limit")
                break
        
        return PullResult(changes=all_changes, total_count=len(all_changes))
```

### Step 6: Enhanced FastAPI Sync Endpoints

**File**: `src/JCSELECT/api/sync.py`

```python
@router.post("/push", response_model=SyncPushResponse)
async def push_changes(
    push_request: SyncPushRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SyncPushResponse:
    """Process client changes with dependency validation"""
    
    processed_count = 0
    failed_changes = []
    conflicts = []
    
    for change in push_request.changes:
        try:
            # Validate FK dependencies
            if not _validate_dependencies(change, db):
                failed_changes.append(change)
                continue
            
            # Check for conflicts
            existing_entity = _get_existing_entity(change, db)
            if existing_entity and existing_entity.updated_at > change.timestamp:
                conflicts.append(change)
                continue
            
            # Apply change
            _apply_entity_change(change, db, current_user.id)
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Failed to process change {change.entity_id}: {e}")
            failed_changes.append(change)
    
    db.commit()
    
    return SyncPushResponse(
        processed_count=processed_count,
        failed_changes=failed_changes,
        conflicts=conflicts,
        server_timestamp=datetime.utcnow()
    )

@router.get("/pull", response_model=SyncPullResponse)
async def pull_changes(
    last_sync: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000, ge=1),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SyncPullResponse:
    """Return paginated server changes since last sync"""
    
    # Build query for all syncable entities
    changes = []
    total_available = 0
    
    for entity_class in [Voter, TallySession, TallyLine, AuditLog, User, Party]:
        entity_changes, entity_total = _get_entity_changes(
            entity_class, last_sync, current_user, db, limit, offset
        )
        changes.extend(entity_changes)
        total_available += entity_total
    
    # Sort by timestamp to maintain consistency
    changes.sort(key=lambda x: x.timestamp)
    
    # Apply pagination
    paginated_changes = changes[offset:offset + limit]
    has_more = (offset + limit) < len(changes)
    
    return SyncPullResponse(
        changes=paginated_changes,
        server_timestamp=datetime.utcnow(),
        has_more=has_more
    )

def _validate_dependencies(change: EntityChange, db: Session) -> bool:
    """Validate that all FK dependencies exist"""
    if change.entity_type == "TallyLine":
        # Check TallySession exists
        session_id = change.data.get("tally_session_id")
        if session_id and not db.get(TallySession, session_id):
            return False
        
        # Check Party exists
        party_id = change.data.get("party_id")
        if party_id and not db.get(Party, party_id):
            return False
    
    # Add more dependency checks as needed
    return True
```

### Step 7: Enhanced Sync Data Models

**File**: `src/JCSELECT/models/sync_schemas.py`

```python
class SyncPushResponse(BaseModel):
    """Enhanced server push response with dependency conflicts"""
    processed_count: int
    failed_changes: List[EntityChange]
    conflicts: List[EntityChange]
    dependency_conflicts: List[EntityChange] = []  # New field
    server_timestamp: datetime

class SyncPullResponse(BaseModel):
    """Enhanced server pull response with pagination"""
    changes: List[EntityChange]
    server_timestamp: datetime
    has_more: bool
    total_available: Optional[int] = None

class DependencyConflictError(Exception):
    """Raised when FK dependencies are missing"""
    def __init__(self, failed_changes: List[EntityChange]):
        self.failed_changes = failed_changes
        super().__init__(f"Dependency conflicts: {len(failed_changes)} changes")
```

### Step 8: UI Integration for Soft Deletes

**File**: `src/JCSELECT/controllers/voter_search_controller.py` (modifications)

```python
def _build_search_query(self, query: str) -> Select:
    """Enhanced search query excluding soft-deleted records"""
    normalized_query = self._normalize_arabic_text(query)
    
    base_query = select(Voter).where(
        Voter.deleted_at.is_(None),  # Exclude soft-deleted
        or_(
            Voter.voter_number == query,
            Voter.voter_number.startswith(query),
            Voter.full_name.contains(normalized_query),
            Voter.father_name.contains(normalized_query)
        )
    )
    
    return base_query.order_by(
        case(
            (Voter.voter_number == query, 1),
            (Voter.voter_number.startswith(query), 2),
            (Voter.full_name.contains(normalized_query), 3),
            else_=4
        )
    ).limit(100)

@Slot(str, str)
def softDeleteVoter(self, voter_id: str, operator_id: str) -> None:
    """Soft delete voter (admin only)"""
    try:
        with get_session() as session:
            soft_delete_voter(voter_id, operator_id, session)
            self.voterDeletedSuccessfully.emit(voter_id)
            self.refreshSearch()
    except Exception as e:
        self.operationFailed.emit(f"Delete failed: {str(e)}")
```

### Step 9: Enhanced Testing Strategy

**Unit Tests for Dependency Handling**:
```python
# tests/unit/test_dependency_ordering.py
class TestDependencyOrdering:
    def test_batch_dependency_order(self):
        """Test changes are batched in correct dependency order"""
        changes = [
            EntityChange(entity_type="TallyLine", ...),
            EntityChange(entity_type="TallySession", ...),
            EntityChange(entity_type="User", ...)
        ]
        
        engine = SyncEngine(settings, queue)
        batches = engine._create_dependency_batches(changes)
        
        # Should be reordered: User, TallySession, TallyLine
        assert batches[0][0].entity_type == "User"
        assert batches[1][0].entity_type == "TallySession"
        assert batches[2][0].entity_type == "TallyLine"
    
    def test_dependency_conflict_handling(self):
        """Test 409 conflicts are handled gracefully"""
        # Test missing FK scenario

# tests/unit/test_soft_deletes.py
class TestSoftDeletes:
    def test_soft_delete_voter(self):
        """Test voter soft delete functionality"""
        
    def test_search_excludes_deleted(self):
        """Test search results exclude soft-deleted records"""
```

**Integration Tests with Pagination**:
```python
# tests/integration/test_paginated_sync.py
class TestPaginatedSync:
    def test_large_dataset_pull(self):
        """Test pulling large datasets with pagination"""
        # Create 500 changes on server
        # Pull with page_size=100
        # Verify all changes retrieved correctly
    
    def test_dependency_conflict_retry(self):
        """Test dependency conflicts are retried correctly"""
        # Push TallyLine before TallySession
        # Verify 409 response
        # Push TallySession
        # Verify TallyLine succeeds on retry
```

## 5. Execution Steps

```bash
# 1. Add soft delete fields to database schema
poetry run alembic revision --autogenerate -m "Add soft delete fields"
poetry run alembic upgrade head

# 2. Update settings configuration
# Edit src/JCSELECT/utils/settings.py (add enhanced sync settings)

# 3. Implement soft delete DAO methods
# Edit src/JCSELECT/dao.py (add soft delete functions)

# 4. Enhance sync queue with dependency ordering
# Edit src/JCSELECT/sync/queue.py

# 5. Enhance sync engine
# Edit src/JCSELECT/sync/engine.py (add dependency batching)

# 6. Update sync data models
# Edit src/JCSELECT/models/sync_schemas.py

# 7. Enhance FastAPI endpoints
# Edit src/JCSELECT/api/sync.py (add dependency validation)

# 8. Update UI controllers for soft deletes
# Edit src/JCSELECT/controllers/voter_search_controller.py

# 9. Create enhanced test suite
# Create tests/unit/test_dependency_ordering.py
# Create tests/unit/test_soft_deletes.py
# Create tests/integration/test_paginated_sync.py

# 10. Add soft delete UI components (admin only)
# Add delete buttons to admin interface
# Update QML to show deletion confirmations

# 11. Run migration and test
poetry run alembic upgrade head
poetry run pytest tests/unit/test_dependency_ordering.py -v
poetry run pytest tests/integration/test_paginated_sync.py -v

# 12. End-to-end testing
poetry run python -m JCSELECT
# Test soft delete functionality
# Test sync with dependency conflicts
# Test pagination with large datasets
```

## 6. Acceptance Criteria

- ✅ All syncable entities support soft deletes with `deleted_at` and `deleted_by` fields
- ✅ UI search and listings exclude soft-deleted records automatically
- ✅ Sync pushes are ordered by entity dependencies (parents before children)
- ✅ Server returns 409 for missing FK dependencies, client retries next cycle
- ✅ Pull endpoint supports pagination with `limit`, `offset`, and `has_more`
- ✅ Large datasets pull completely through multiple paginated requests
- ✅ Entity-level conflict resolution works with timestamp comparison
- ✅ All conflicts logged to AuditLog with full before/after details
- ✅ Soft delete operations sync correctly between client and server
- ✅ Dependency conflict retry logic prevents infinite loops
- ✅ Background sync handles network failures with exponential backoff
- ✅ JWT authentication with role-based access control works
- ✅ Admin can soft delete entities, operators cannot
- ✅ All sync operations maintain audit trail integrity
- ✅ Client handles paginated responses without data loss
