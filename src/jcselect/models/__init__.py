"""
jcselect.models package

• Re-exports the main ORM classes for easy import.
• Dynamically imports every module in this package so SQLAlchemy sees
  all mappers before metadata is used (tests, Alembic, etc.).
"""
import pkgutil
from importlib import import_module
from pathlib import Path

# ------------------------------------------------------------------
# 1. Dynamically import every .py file in this package
# ------------------------------------------------------------------
_pkg_path = Path(__file__).resolve().parent
for module_info in pkgutil.iter_modules([str(_pkg_path)]):
    if not module_info.ispkg:
        import_module(f"{__name__}.{module_info.name}")

# ------------------------------------------------------------------
# 2. Normal explicit imports / re-exports (order no longer matters)
# ------------------------------------------------------------------
from .audit_log import AuditLog
from .base import BaseUUIDModel, TimeStampedMixin
from .enums import BallotType
from .party import Party
from .pen import Pen
from .results import CandidateTotal, PartyTotal, ResultAggregate, WinnerEntry
from .tally_line import TallyLine
from .tally_session import TallySession
from .user import User
from .voter import Voter

__all__ = [
    "BaseUUIDModel",
    "TimeStampedMixin",
    "AuditLog",
    "BallotType",
    "Party",
    "Pen",
    "TallyLine",
    "TallySession",
    "User",
    "Voter",
    # Results models
    "ResultAggregate",
    "PartyTotal",
    "CandidateTotal",
    "WinnerEntry",
]
