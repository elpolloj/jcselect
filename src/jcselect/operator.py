"""Operator application entry point."""
from __future__ import annotations

import os
import sys


def main_operator() -> int:
    """Launch jcselect in operator mode."""
    # Set environment variables to force operator mode
    os.environ["JCSELECT_MODE"] = "operator"
    os.environ["JCSELECT_REQUIRED_ROLE"] = "operator"

    print("👤 Starting jcselect in Operator mode")
    
    # Import main only when needed to avoid circular import
    from jcselect.main import main
    return main()


if __name__ == "__main__":
    sys.exit(main_operator())
