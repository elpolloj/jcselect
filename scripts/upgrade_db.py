#!/usr/bin/env python3
"""Database migration upgrade script.

This script runs Alembic migrations to upgrade the database to the latest schema.
"""
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Run alembic upgrade head."""
    try:
        # Change to project root directory
        project_root = Path(__file__).parent.parent

        print("🔄 Running database migrations...")

        # Run alembic upgrade head
        result = subprocess.run(
            ["poetry", "run", "alembic", "upgrade", "head"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )

        print("✅ Database migrations completed successfully!")

        # Print alembic output if there was any
        if result.stdout.strip():
            print("\nAlembic output:")
            print(result.stdout)

    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed with exit code {e.returncode}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
