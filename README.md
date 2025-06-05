# JCSELECT

Offline-first desktop voter tracking application for Lebanon.

## Setup

### Install Dependencies

```bash
poetry install
```

### Run Migrations

To set up the database schema:

```bash
# Option 1: Using the helper script
poetry run python scripts/upgrade_db.py

# Option 2: Using Alembic directly
poetry run alembic upgrade head
```

This will create the SQLite database at `~/.jcselect/local.db` with all required tables.

### Check Database

To verify the database was created correctly:

```bash
poetry run python scripts/check_db.py
```

### Seed Database

To populate the database with demo data (3 pens, 20 parties, 2 users, 100 voters):

```bash
poetry run python scripts/seed_demo_data.py
```

This script is idempotent - running it multiple times will not create duplicate data.

## Development

### Code Quality

```bash
# Run linting and formatting
poetry run pre-commit run --all-files

# Type checking
poetry run mypy src/

# Run tests
poetry run pytest
```

### Database Migrations

```bash
# Generate new migration after model changes
poetry run alembic revision --autogenerate -m "Description of changes"

# Apply migrations
poetry run alembic upgrade head
```
