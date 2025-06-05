"""Admin application entry point."""
from __future__ import annotations

import os
import sys

from jcselect.main import main


def main_admin() -> int:
    """Launch jcselect in admin mode."""
    # Set environment variables to force admin mode
    os.environ["JCSELECT_MODE"] = "admin"
    os.environ["JCSELECT_REQUIRED_ROLE"] = "admin"

    print("🔑 Starting jcselect in Admin mode")
    return main()


if __name__ == "__main__":
    sys.exit(main_admin())
