"""Logging configuration for jcselect application."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger


def setup_logging(debug: bool = False, log_dir: Path | None = None) -> None:
    """Configure logging for the application.

    Args:
        debug: Enable debug mode with verbose logging
        log_dir: Directory for log files (defaults to logs/ in current dir)
    """
    # Remove default handler
    logger.remove()

    # Console logging
    console_level = "DEBUG" if debug else "INFO"
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=console_format,
        level=console_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # File logging
    if log_dir is None:
        log_dir = Path("logs")

    log_dir.mkdir(exist_ok=True)

    # General application log
    logger.add(
        log_dir / "jcselect.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG" if debug else "INFO",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )

    # Performance-specific log
    logger.add(
        log_dir / "performance.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="5 MB",
        retention="7 days",
        compression="zip",
        filter=lambda record: "performance" in record["message"].lower() or "executed in" in record["message"].lower(),
    )

    # Error log
    logger.add(
        log_dir / "errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="WARNING",
        rotation="5 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )

    if debug:
        logger.info("Debug logging enabled")
        logger.debug(f"Log files will be written to: {log_dir.absolute()}")
    else:
        logger.info("Logging configured")


def get_debug_mode() -> bool:
    """Get debug mode from environment or settings."""
    # Check environment variable first
    if os.getenv("JCSELECT_DEBUG", "").lower() in ("1", "true", "yes", "on"):
        return True

    # Try to import settings
    try:
        from jcselect.config.settings import DEBUG
        return DEBUG
    except ImportError:
        return False


def configure_app_logging() -> None:
    """Configure application logging with appropriate settings."""
    debug = get_debug_mode()
    setup_logging(debug=debug)

    if debug:
        logger.info("🔧 Debug mode enabled - verbose logging active")

    logger.info("🚀 jcselect application logging initialized")
