#!/usr/bin/env python3
"""Check database tables script."""
import sqlite3
from pathlib import Path


def main() -> None:
    """Check what tables exist in the database."""
    db_path = Path.home() / ".jcselect" / "local.db"

    if not db_path.exists():
        print(f"❌ Database file not found at: {db_path}")
        return

    print(f"📁 Database file found at: {db_path}")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print(f"📊 Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")

        conn.close()

    except Exception as e:
        print(f"❌ Error checking database: {e}")


if __name__ == "__main__":
    main()
