# JCSELECT Domain Schema - Technical Specification

## 1. Overview

Establish the local/offline database layer and mirror the core MSSQL schema so the Python app can search voters, mark them as voted, store end-of-day candidate tallies, and record operator log-ins/actions.

## 2. Technical Requirements

### 2.1 Database Engines
- **Primary**: SQLite for offline desktop operations (`~/.jcselect/local.db`)
- **Secondary**: MSSQL for server (VPS) via `pyodbc` and ODBC Driver 18
- **ORM**: SQLModel with Alembic migrations
- **Connection Management**: Context managers for session handling

### 2.2 Core Entities Schema

#### 2.2.1 Pen (Polling Booth)
```
- id: UUID (primary key)
- town_name: str (required)
- label: str (required, e.g., "Pen 101")
- created_at: datetime
- updated_at: datetime (auto-update)
```

#### 2.2.2 User (Operators)
```
- id: UUID (primary key)
- username: str (unique, required)
- password_hash: str (required, bcrypt)
- full_name: str (required)
- role: str (default "operator")
- is_active: bool (default True)
- created_at: datetime
- updated_at: datetime (auto-update)
```

#### 2.2.3 Voter (≈ legacy mlist)
```
- id: UUID (primary key)
- pen_id: UUID (foreign key to Pen)
- voter_number: str (required, unique within pen)
- full_name: str (required)
- father_name: str (optional)
- mother_name: str (optional)
- birth_year: int (optional)
- gender: str (optional, M/F)
- has_voted: bool (default False)
- voted_at: datetime (nullable)
- voted_by_operator_id: UUID (nullable, foreign key to User)
- created_at: datetime
- updated_at: datetime (auto-update)
```

#### 2.2.4 Party (Candidates/Parties)
```
- id: UUID (primary key)
- name: str (required, unique)
- short_code: str (optional, e.g., "LF", "FPM")
- display_order: int (default 0)
- is_active: bool (default True)
- created_at: datetime
- updated_at: datetime (auto-update)
```

#### 2.2.5 TallySession (Counting Event)
```
- id: UUID (primary key)
- pen_id: UUID (foreign key to Pen)
- session_name: str (required, e.g., "End of Day Count")
- started_at: datetime (required)
- completed_at: datetime (nullable)
- operator_id: UUID (foreign key to User)
- total_votes_counted: int (default 0)
- notes: str (optional)
- created_at: datetime
- updated_at: datetime (auto-update)
```

#### 2.2.6 TallyLine (Dynamic Votes per Party)
```
- id: UUID (primary key)
- tally_session_id: UUID (foreign key to TallySession)
- party_id: UUID (foreign key to Party)
- vote_count: int (required, default 0)
- created_at: datetime
- updated_at: datetime (auto-update)
- UNIQUE constraint on (tally_session_id, party_id)
```

#### 2.2.7 AuditLog
```
- id: UUID (primary key)
- operator_id: UUID (foreign key to User)
- action: str (required, e.g., "VOTER_MARKED", "TALLY_CREATED")
- entity_type: str (required, e.g., "Voter", "TallySession")
- entity_id: UUID (required)
- old_values: JSON (nullable)
- new_values: JSON (nullable)
- timestamp: datetime (required)
- ip_address: str (optional)
- user_agent: str (optional)
```

### 2.3 Database Configuration
- **SQLite Path**: `~/.jcselect/local.db`
- **MSSQL Connection**: Via environment variable `DATABASE_URL`
- **Connection Pooling**: SQLAlchemy engine with appropriate pool settings
- **Migration Tool**: Alembic with SQLModel metadata integration

## 3. Detailed Implementation Plan

### Step 1: Database Utilities Setup

**File**: `src/JCSELECT/utils/db.py`

**Components**:
- `DatabaseConfig` class with driver detection logic
- `get_engine()` function that reads `settings.DB_DRIVER` (defaults to "sqlite")
- `get_session()` context manager for session lifecycle
- Connection string builders for both SQLite and MSSQL
- Engine factory with appropriate pool settings per database type

**Configuration Logic**:
- SQLite: `sqlite:///{user_home}/.jcselect/local.db`
- MSSQL: Read from `DATABASE_URL` environment variable
- Automatic directory creation for SQLite database path
- Connection validation and retry logic

### Step 2: SQLModel Entity Definitions

**File Structure Options**:
- Option A: Single `src/JCSELECT/models.py` file
- Option B: `src/JCSELECT/models/` package with separate files per entity

**Implementation Details**:
- All entities inherit from SQLModel base class
- UUID primary keys using `uuid4()` as default factory
- `created_at` and `updated_at` timestamps with `func.now()` defaults
- `updated_at` with `onupdate=func.now()` for automatic updates
- Proper foreign key relationships with cascade options
- Index definitions for frequently queried fields (voter_number, username)
- Validation constraints using Pydantic validators

**Relationships**:
- `Pen.voters`: One-to-many relationship with Voter
- `User.voted_voters`: One-to-many relationship with Voter (via voted_by_operator_id)
- `TallySession.tally_lines`: One-to-many relationship with TallyLine
- `TallySession.pen`: Many-to-one relationship with Pen
- `TallyLine.party`: Many-to-one relationship with Party

### Step 3: Alembic Migration Setup

**Initialization**:
- Run `alembic init alembic` in project root
- Configure `alembic/env.py` to import SQLModel metadata
- Set up `alembic.ini` with SQLAlchemy URL configuration
- Create template for migration file naming convention

**Migration Configuration**:
- Import all model classes in `env.py`
- Configure `target_metadata = SQLModel.metadata`
- Set up offline and online migration modes
- Configure database URL resolution from environment
- Add support for both SQLite and MSSQL in migration context

**First Migration**:
- Generate initial migration: `alembic revision --autogenerate -m "Initial schema"`
- Review generated migration for accuracy
- Test migration on both SQLite and MSSQL (if available)

### Step 4: Data Access Object Implementation

**File**: `src/JCSELECT/dao.py`

**Core Functions**:
- `upsert(model_instance, session)`: Generic upsert that works on both SQLite and MSSQL
- `mark_voted(voter_id, operator_id, session)`: Atomic voter marking with audit trail
- `create_tally_session(pen_id, operator_id, session_name, session)`: Initialize counting session
- `update_tally_line(session_id, party_id, vote_count, session)`: Upsert vote counts
- `get_voter_by_number(pen_id, voter_number, session)`: Voter lookup
- `get_pen_voters(pen_id, session, voted_only=False)`: Pen voter listing

**Error Handling**:
- Database constraint violation handling
- Transaction rollback on errors
- Specific exception types for business logic errors
- Logging integration for all database operations

**Audit Trail Integration**:
- Automatic audit log creation for sensitive operations
- Before/after value capture for updates
- Operator tracking for all modifications

### Step 5: Demo Data Seeding Script

**File**: `scripts/seed_demo_data.py`

**Data Generation**:
- Create one test town: "TestTown"
- Generate 3 pens: "Pen 101", "Pen 102", "Pen 103"
- Create 20 political parties with realistic Lebanese party names
- Generate 100 fake voters distributed across the 3 pens
- Create 2 operator users: "admin" and "operator1"

**Data Characteristics**:
- Realistic Lebanese names using faker or predefined lists
- Balanced gender distribution
- Varied birth years (1950-2005)
- Sequential voter numbers within each pen
- Some voters pre-marked as voted for testing

**Execution Flow**:
- Check if data already exists (avoid duplicates)
- Create data in proper dependency order
- Print summary of created records
- Validate data integrity after creation

### Step 6: Test Infrastructure

**Test Database Setup**:
- In-memory SQLite database for tests
- Pytest fixtures for database session management
- Automatic schema creation and teardown
- Seed data fixtures for consistent test state

**Test Files**:

**`tests/unit/test_dao_mark_voted.py`**:
- Test successful voter marking
- Test duplicate marking prevention
- Test operator tracking
- Test audit log creation
- Test transaction rollback on errors

**`tests/unit/test_tally_line_upsert.py`**:
- Test tally session creation
- Test tally line insertion and updates
- Test vote count aggregation
- Test constraint validation
- Test concurrent access scenarios

**`tests/integration/test_database_engines.py`**:
- Test SQLite engine functionality
- Test MSSQL engine functionality (if available)
- Test migration execution
- Test cross-engine data compatibility

### Step 7: Dependencies and Configuration

**Runtime Dependencies Addition**:
- Add `pyodbc` to `[tool.poetry.dependencies]`
- Add `alembic` (already included in bootstrap)
- Add `bcrypt` for password hashing
- Add `faker` to dev dependencies for data generation

**Environment Configuration**:
- Document ODBC Driver 18 installation requirements
- Add environment variable documentation
- Create `.env.example` file with sample configuration
- Update README with database setup instructions

**Settings Management**:
- Create `src/JCSELECT/utils/settings.py` for configuration
- Environment variable loading with defaults
- Database URL validation and parsing
- Configuration validation on startup


## 4. Execution Steps

```bash
# 1. Add new dependencies
poetry add pyodbc alembic bcrypt
poetry add --group dev faker

# 2. Create database utilities
# - src/JCSELECT/utils/db.py
# - src/JCSELECT/utils/settings.py

# 3. Define SQLModel entities
# - src/JCSELECT/models.py (or models/ package)

# 4. Initialize Alembic
alembic init alembic
# - Configure alembic/env.py
# - Update alembic.ini

# 5. Generate first migration
alembic revision --autogenerate -m "Initial schema"

# 6. Implement DAO layer
# - src/JCSELECT/dao.py

# 7. Create seeding script
# - scripts/seed_demo_data.py

# 8. Add test infrastructure
# - tests/conftest.py (update with DB fixtures)
# - tests/unit/test_dao_mark_voted.py
# - tests/unit/test_tally_line_upsert.py
# - tests/integration/test_database_engines.py

# 9. Update configuration files
# - .gitignore
# - README.md
# - .env.example

# 10. Run migration and seed
poetry run alembic upgrade head
poetry run python scripts/seed_demo_data.py

# 11. Execute tests
poetry run pytest -q

# 12. Run code quality checks
poetry run pre-commit run --all-files
```

## 5. Acceptance Criteria

- ✅ `alembic upgrade head` runs without error against both SQLite and MSSQL (when `DATABASE_URL` is set)
- ✅ `python scripts/seed_demo_data.py` inserts rows and prints a success summary
- ✅ `pytest -q` exits 0 with ≥ 2 tests collected
- ✅ All ruff/black/mypy hooks pass
- ✅ Database file `~/.jcselect/local.db` is created and populated
- ✅ DAO functions successfully manipulate data in tests
- ✅ Audit logging captures all sensitive operations
- ✅ Both SQLite and MSSQL engines work with the same codebase

## 6. Open Questions

- **MSSQL Testing**: How to set up MSSQL test environment for CI?
- **Migration Strategy**: How to handle schema changes in production?
- **Performance**: Should we add database indexing optimization?
- **Backup Strategy**: Should we implement automatic database backup?

This specification provides a comprehensive foundation for the database layer while maintaining compatibility with both offline SQLite and online MSSQL operations.
