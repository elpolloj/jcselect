"""Results aggregation DAO functions for live results."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from loguru import logger
from sqlmodel import Session, func, select

from jcselect.models import Party, Pen, TallyLine, TallySession, Voter
from jcselect.utils.db import get_session


def _aggregate_results(pen_id: str | None = None, session: Session | None = None) -> list[dict[str, Any]]:
    """
    Internal utility to query the v_results_aggregate view with optional pen filtering.

    Args:
        pen_id: Optional pen ID to filter results by (hex format without hyphens)
        session: Database session, if None will create one

    Returns:
        List of raw result dictionaries from the view
    """
    should_close_session = session is None
    if session is None:
        session = next(get_session())

    try:
        from sqlalchemy import text

        if pen_id:
            # Filter by specific pen
            query = text("""
                SELECT pen_id, party_id, candidate_id, ballot_type, votes, ballot_count, last_updated
                FROM v_results_aggregate
                WHERE pen_id = :pen_id
                ORDER BY votes DESC
            """)
            result = session.execute(query, {"pen_id": pen_id})
        else:
            # All pens
            query = text("""
                SELECT pen_id, party_id, candidate_id, ballot_type, votes, ballot_count, last_updated
                FROM v_results_aggregate
                ORDER BY votes DESC
            """)
            result = session.execute(query)

        rows = result.fetchall()

        # Convert to dictionaries
        columns = result.keys()
        results = [dict(zip(columns, row, strict=False)) for row in rows]

        logger.debug(f"Retrieved {len(results)} aggregate results")
        return results

    except Exception as e:
        logger.error(f"Failed to query results aggregate: {e}")
        return []
    finally:
        if should_close_session:
            session.close()


def get_totals_by_party(pen_id: str | None = None, session: Session | None = None) -> list[dict[str, Any]]:
    """
    Get party-level vote totals from the v_results_aggregate view.

    Args:
        pen_id: Optional pen ID to filter results by (UUID as string)
        session: Optional database session, if None will create one

    Returns:
        List of PartyTotal-compatible dictionaries sorted by votes DESC
    """
    should_close_session = session is None
    if session is None:
        session = next(get_session())

    try:
        # Convert UUID to hex format if provided
        pen_id_hex = None
        if pen_id:
            try:
                pen_id_hex = UUID(pen_id).hex
            except ValueError:
                # Already in hex format
                pen_id_hex = pen_id

        # Get raw results from view
        raw_results = _aggregate_results(pen_id_hex, session)

        # Aggregate by party
        party_totals = {}
        for row in raw_results:
            party_id = row.get('party_id')
            if not party_id:
                continue  # Skip special ballots

            party_id_str = party_id.replace('-', '') if isinstance(party_id, str) else str(party_id)
            votes = row.get('votes', 0)

            if party_id_str not in party_totals:
                # Get party name
                party = session.get(Party, party_id)
                party_name = party.name if party else f"Party {party_id_str[:8]}"

                party_totals[party_id_str] = {
                    "party_id": party_id_str,
                    "party_name": party_name,
                    "total_votes": 0,
                    "candidate_count": 0,
                    "pen_breakdown": {}
                }

            party_totals[party_id_str]["total_votes"] += votes
            if row.get('candidate_id'):  # Only count actual candidates
                party_totals[party_id_str]["candidate_count"] += 1

            # Add pen breakdown if multiple pens
            if not pen_id:
                pen_id_from_row = row.get('pen_id', '')
                if pen_id_from_row:
                    party_totals[party_id_str]["pen_breakdown"][pen_id_from_row] = votes

        # Sort by total votes descending
        sorted_parties = sorted(
            party_totals.values(),
            key=lambda x: x["total_votes"],
            reverse=True
        )

        logger.debug(f"Generated {len(sorted_parties)} party totals")
        return sorted_parties

    except Exception as e:
        logger.error(f"Failed to get party totals: {e}")
        return []
    finally:
        if should_close_session:
            session.close()


def get_totals_by_candidate(pen_id: str | None = None, session: Session | None = None) -> list[dict[str, Any]]:
    """
    Get candidate-level vote totals from the v_results_aggregate view.

    Args:
        pen_id: Optional pen ID to filter results by (UUID as string)
        session: Optional database session, if None will create one

    Returns:
        List of CandidateTotal-compatible dictionaries sorted by votes DESC
    """
    should_close_session = session is None
    if session is None:
        session = next(get_session())

    try:
        # Convert UUID to hex format if provided
        pen_id_hex = None
        if pen_id:
            try:
                pen_id_hex = UUID(pen_id).hex
            except ValueError:
                # Already in hex format
                pen_id_hex = pen_id

        # Get raw results from view
        raw_results = _aggregate_results(pen_id_hex, session)

        # Aggregate by candidate
        candidate_totals = {}
        for row in raw_results:
            candidate_id = row.get('candidate_id')
            if not candidate_id:
                continue  # Skip party-only votes

            candidate_id_str = candidate_id.replace('-', '') if isinstance(candidate_id, str) else str(candidate_id)
            party_id = row.get('party_id')
            votes = row.get('votes', 0)

            if candidate_id_str not in candidate_totals:
                # Get party name
                party = session.get(Party, party_id) if party_id else None
                party_name = party.name if party else f"Party {str(party_id)[:8]}"
                party_id_str = party_id.replace('-', '') if isinstance(party_id, str) else str(party_id)

                candidate_totals[candidate_id_str] = {
                    "candidate_id": candidate_id_str,
                    "candidate_name": f"Candidate {candidate_id_str[:8]}",  # Mock name for now
                    "party_id": party_id_str,
                    "party_name": party_name,
                    "total_votes": 0,
                    "pen_breakdown": {}
                }

            candidate_totals[candidate_id_str]["total_votes"] += votes

            # Add pen breakdown if multiple pens
            if not pen_id:
                pen_id_from_row = row.get('pen_id', '')
                if pen_id_from_row:
                    candidate_totals[candidate_id_str]["pen_breakdown"][pen_id_from_row] = votes

        # Sort by total votes descending
        sorted_candidates = sorted(
            candidate_totals.values(),
            key=lambda x: x["total_votes"],
            reverse=True
        )

        logger.debug(f"Generated {len(sorted_candidates)} candidate totals")
        return sorted_candidates

    except Exception as e:
        logger.error(f"Failed to get candidate totals: {e}")
        return []
    finally:
        if should_close_session:
            session.close()


def get_pen_completion_status(pen_id: str, session: Session | None = None) -> bool:
    """
    Check if a pen's tally counting is complete.

    Args:
        pen_id: Pen ID (UUID as string)
        session: Optional database session, if None will create one

    Returns:
        True if tally session exists and ballot counting appears complete
    """
    should_close_session = session is None
    if session is None:
        session = next(get_session())

    try:
        # Convert to UUID
        try:
            pen_uuid = UUID(pen_id)
        except ValueError:
            logger.error(f"Invalid pen_id format: {pen_id}")
            return False

        # Get pen to check expected ballots
        pen = session.get(Pen, pen_uuid)
        if not pen:
            logger.error(f"Pen {pen_id} not found")
            return False

        # Get active tally session for this pen
        stmt = select(TallySession).where(
            TallySession.pen_id == pen_uuid,
            TallySession.deleted_at.is_(None)
        )
        tally_session = session.exec(stmt).first()

        if not tally_session:
            logger.debug(f"No tally session found for pen {pen_id}")
            return False

        # Check if we have expected number of ballots
        # Count actual voters in the pen as expected ballots
        voter_count_result = session.execute(
            select(func.count()).select_from(Voter).where(
                Voter.pen_id == pen_uuid,
                Voter.deleted_at.is_(None)
            )
        ).scalar()
        expected_ballots = voter_count_result or 0

        if expected_ballots == 0:
            # If no voters, consider complete if any tally lines exist
            stmt = select(TallyLine).where(
                TallyLine.tally_session_id == tally_session.id,
                TallyLine.deleted_at.is_(None)
            )
            tally_lines = session.exec(stmt).all()
            is_complete = len(tally_lines) > 0
        else:
            # Check if ballot_number >= expected
            current_ballot = getattr(tally_session, 'ballot_number', 0)
            is_complete = current_ballot >= expected_ballots

        logger.debug(f"Pen {pen_id} completion status: {is_complete}")
        return is_complete

    except Exception as e:
        logger.error(f"Failed to check pen completion status: {e}")
        return False
    finally:
        if should_close_session:
            session.close()


def get_pen_voter_turnout(pen_id: str, session: Session | None = None) -> dict[str, int]:
    """
    Get voter turnout statistics for a pen.

    Args:
        pen_id: Pen ID (UUID as string)
        session: Optional database session, if None will create one

    Returns:
        Dictionary with keys: total_ballots, white, cancel, illegal, blank
    """
    should_close_session = session is None
    if session is None:
        session = next(get_session())

    try:
        # Convert to UUID
        try:
            pen_uuid = UUID(pen_id)
        except ValueError:
            logger.error(f"Invalid pen_id format: {pen_id}")
            return {"total_ballots": 0, "white": 0, "cancel": 0, "illegal": 0, "blank": 0}

        # Get active tally session for this pen
        stmt = select(TallySession).where(
            TallySession.pen_id == pen_uuid,
            TallySession.deleted_at.is_(None)
        )
        tally_session = session.exec(stmt).first()

        if not tally_session:
            logger.debug(f"No tally session found for pen {pen_id}")
            return {"total_ballots": 0, "white": 0, "cancel": 0, "illegal": 0, "blank": 0}

        # Get all tally lines for this session
        stmt = select(TallyLine).where(
            TallyLine.tally_session_id == tally_session.id,
            TallyLine.deleted_at.is_(None)
        )
        tally_lines = session.exec(stmt).all()

        # Aggregate by ballot type
        turnout = {
            "total_ballots": 0,
            "white": 0,
            "cancel": 0,
            "illegal": 0,
            "blank": 0
        }

        for line in tally_lines:
            ballot_type = line.ballot_type.value if line.ballot_type else "normal"
            vote_count = line.vote_count

            turnout["total_ballots"] += vote_count

            if ballot_type in turnout:
                turnout[ballot_type] += vote_count

        logger.debug(f"Calculated turnout for pen {pen_id}: {turnout}")
        return turnout

    except Exception as e:
        logger.error(f"Failed to get pen voter turnout: {e}")
        return {"total_ballots": 0, "white": 0, "cancel": 0, "illegal": 0, "blank": 0}
    finally:
        if should_close_session:
            session.close()


def calculate_winners(pen_id: str | None = None, seats: int = 3, session: Session | None = None) -> list[dict[str, Any]]:
    """
    Calculate election winners based on candidate vote totals.

    Args:
        pen_id: Optional pen ID to filter by (UUID as string)
        seats: Number of seats available (default 3 for Lebanese elections)
        session: Optional database session, if None will create one

    Returns:
        List of WinnerEntry-compatible dictionaries with rank and is_elected status
    """
    should_close_session = session is None
    if session is None:
        session = next(get_session())

    try:
        # Get candidate totals
        candidate_totals = get_totals_by_candidate(pen_id, session)

        # Convert to winner entries with ranking
        winners = []
        for rank, candidate in enumerate(candidate_totals, 1):
            is_elected = rank <= seats

            winner_entry = {
                "candidate_id": candidate["candidate_id"],
                "candidate_name": candidate["candidate_name"],
                "party_name": candidate["party_name"],
                "total_votes": candidate["total_votes"],
                "rank": rank,
                "is_elected": is_elected
            }
            winners.append(winner_entry)

        logger.debug(f"Calculated {len(winners)} winner entries, {seats} elected")
        return winners

    except Exception as e:
        logger.error(f"Failed to calculate winners: {e}")
        return []
    finally:
        if should_close_session:
            session.close()
