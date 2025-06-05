#!/usr/bin/env python3
"""Quick run script for smoke testing jcselect application."""

import sys
import os
from pathlib import Path

# Add the src directory to Python path so jcselect can be imported
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set up environment for testing
os.environ.setdefault("JCSELECT_MODE", "operator")
os.environ.setdefault("SYNC_API_URL", "http://localhost:8000")
os.environ.setdefault("SYNC_JWT_SECRET", "test-secret-key-for-development-only-32-chars-long")
os.environ.setdefault("SYNC_ENABLED", "false")  # Disable sync for smoke test

def main():
    """Run the jcselect application."""
    try:
        from jcselect.main import main as app_main
        print("🚀 Starting jcselect smoke test...")
        return app_main()
    except ImportError as e:
        print(f"❌ Failed to import jcselect: {e}")
        print("Make sure you're running from the project root directory")
        return 1
    except Exception as e:
        print(f"❌ Application failed to start: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 