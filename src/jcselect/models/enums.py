"""Enums for jcselect models."""
from enum import Enum


class BallotType(str, Enum):
    """Ballot type enumeration for tally counting."""

    NORMAL = "normal"     # Regular candidate ballot
    CANCEL = "cancel"     # Cancelled/invalid ballot
    WHITE = "white"       # White/blank ballot (Lebanese election term)
    ILLEGAL = "illegal"   # Illegal/improper ballot
    BLANK = "blank"       # Blank ballot (no selections)
