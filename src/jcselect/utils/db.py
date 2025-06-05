"""Database connection configuration and utilities."""
from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session

from jcselect.utils.settings import settings


def get_sqlite_path() -> Path:
    """Get the SQLite database file path."""
    db_path = Path.home() / ".jcselect" / "local.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


@dataclass
class DatabaseConfig:
    """Database configuration with driver detection logic."""

    driver: str
    user: str
    password: str
    host: str
    port: int
    database: str

    @classmethod
    def from_settings(cls) -> DatabaseConfig:
        """Create DatabaseConfig from application settings."""
        return cls(
            driver=settings.DB_DRIVER,
            user=settings.DB_USER,
            password=settings.DB_PASS,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
        )

    def get_connection_url(self) -> str:
        """Get the appropriate connection URL based on driver."""
        if self.driver == "sqlite":
            # Create SQLite database path
            db_path = get_sqlite_path()
            return f"sqlite:///{db_path}"

        elif self.driver == "mssql":
            # Create MSSQL connection URL
            url = URL.create(
                "mssql+pyodbc",
                username=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                database=self.database,
                query={"driver": "ODBC Driver 18 for SQL Server"},
            )
            return str(url)

        else:
            raise ValueError(f"Unsupported database driver: {self.driver}")


def get_engine(echo: bool = False, max_retries: int = 3) -> Engine:
    """
    Get SQLAlchemy engine with appropriate configuration.

    Args:
        echo: Whether to echo SQL statements
        max_retries: Maximum number of connection retries

    Returns:
        Configured SQLAlchemy engine

    Raises:
        OperationalError: If connection fails after retries
    """
    config = DatabaseConfig.from_settings()
    connection_url = config.get_connection_url()

    # Configure engine based on driver
    if config.driver == "sqlite":
        engine_kwargs = {
            "echo": echo,
            "pool_pre_ping": True,
            "connect_args": {"check_same_thread": False},
        }
    else:  # mssql
        engine_kwargs = {
            "echo": echo,
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 10,
        }

    engine = create_engine(connection_url, **engine_kwargs)

    # Test connection with retries
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"Database connection established using {config.driver}")
            return engine

        except OperationalError as e:
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff
                logger.warning(
                    f"Database connection attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"Database connection failed after {max_retries} attempts: {e}"
                )
                raise

    return engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for SQLModel session lifecycle.

    Yields:
        SQLModel Session instance

    Raises:
        Exception: Re-raises any exception after rollback
    """
    engine = get_engine()
    session = Session(engine)

    try:
        logger.debug("Database session started")
        yield session
        session.commit()
        logger.debug("Database session committed")

    except Exception as e:
        session.rollback()
        logger.error(f"Database session rolled back due to error: {e}")
        raise

    finally:
        session.close()
        logger.debug("Database session closed")


# Legacy CLOUD_URL for backward compatibility
CLOUD_URL = URL.create(
    "mssql+pyodbc",
    username=settings.DB_USER,
    password=settings.DB_PASS,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
    query={"driver": "ODBC Driver 18 for SQL Server"},
)
