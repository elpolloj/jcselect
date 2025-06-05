#!/usr/bin/env python3
"""Live Results Demo Script

Seeds 1k random ballots → triggers fast-sync → prints top-3 winners live.

Usage:
    python scripts/demo_live_results_loop.py [--iterations=5] [--ballots=1000]
"""

import argparse
import asyncio
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Add src to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from loguru import logger

from jcselect.models import BaseUUIDModel, TimeStampedMixin, Pen, Party, User, TallySession, TallyLine
from jcselect.dao_results import get_totals_by_party, get_totals_by_candidate, calculate_winners
from jcselect.sync.engine import SyncEngine


class LiveResultsDemo:
    """Demo class for live results and winner calculation."""

    def __init__(self, db_url: str = "sqlite:///demo_live_results.db"):
        """Initialize demo with database connection."""
        self.db_url = db_url
        self.engine = create_engine(db_url, echo=False)
        BaseUUIDModel.metadata.create_all(self.engine)
        
        self.Session = sessionmaker(bind=self.engine)
        
        # Track demo data
        self.pens: List[Pen] = []
        self.parties: List[Party] = []
        self.users: List[User] = []
        self.tally_sessions: List[TallySession] = []
        
        # Track results
        self.previous_winners: List[Dict[str, Any]] = []

    def setup_demo_data(self) -> None:
        """Create initial demo data: pens, parties, candidates."""
        session = self.Session()
        
        try:
            logger.info("Setting up demo data...")
            
            # Clear existing data
            session.execute(text("DELETE FROM tally_lines"))
            session.execute(text("DELETE FROM tally_sessions"))
            session.execute(text("DELETE FROM users"))
            session.execute(text("DELETE FROM parties"))
            session.execute(text("DELETE FROM pens"))
            session.commit()
            
            # Create 3 pens
            pen_names = ["Central Voting Station", "North Community Center", "South School"]
            for i, name in enumerate(pen_names):
                pen = Pen(
                    id=str(uuid.uuid4()),
                    town_name=f"District {i+1}",
                    label=name,
                    capacity=1000
                )
                self.pens.append(pen)
                session.add(pen)
            
            # Create 5 parties with realistic Lebanese party names
            party_data = [
                ("Future Movement", "FM", "#0066CC"),
                ("Lebanese Forces", "LF", "#FF6600"),
                ("Free Patriotic Movement", "FPM", "#FF9900"), 
                ("Amal Movement", "Amal", "#009900"),
                ("Hezbollah", "HB", "#FFD700")
            ]
            
            for name, abbr, color in party_data:
                party = Party(
                    id=str(uuid.uuid4()),
                    name=name,
                    abbreviation=abbr,
                    color=color
                )
                self.parties.append(party)
                session.add(party)
            
            session.flush()  # Get IDs
            
            # Create users and tally sessions
            for pen in self.pens:
                user = User(
                    id=str(uuid.uuid4()),
                    username=f"operator_{pen.label.lower().replace(' ', '_')}",
                    password_hash="demo_hash",
                    full_name=f"Demo Operator - {pen.label}",
                    role="operator"
                )
                self.users.append(user)
                session.add(user)
                
                tally_session = TallySession(
                    id=str(uuid.uuid4()),
                    pen_id=pen.id,
                    operator_id=user.id,
                    created_at=datetime.now(timezone.utc),
                    status="active"
                )
                self.tally_sessions.append(tally_session)
                session.add(tally_session)
            
            session.commit()
            
            logger.info(f"Created {len(self.pens)} pens, {len(self.parties)} parties")
            
        finally:
            session.close()

    def seed_random_ballots(self, ballot_count: int = 1000) -> List[str]:
        """Seed random ballots and return list of tally line IDs."""
        session = self.Session()
        tally_line_ids = []
        
        try:
            logger.info(f"Seeding {ballot_count} random ballots...")
            
            # Generate realistic vote distributions
            random.seed()  # Use current time as seed for randomness
            
            for i in range(ballot_count):
                # Pick random pen and its tally session
                pen = random.choice(self.pens)
                tally_session = next(ts for ts in self.tally_sessions if ts.pen_id == pen.id)
                
                # Create tally line with realistic vote count (1-10 votes per ballot)
                tally_line = TallyLine(
                    id=str(uuid.uuid4()),
                    tally_session_id=tally_session.id,
                    party_id=random.choice(self.parties).id,
                    ballot_type="regular",
                    vote_count=random.randint(1, 10),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                session.add(tally_line)
                tally_line_ids.append(tally_line.id)
                
                # Commit in batches for better performance
                if (i + 1) % 100 == 0:
                    session.commit()
                    logger.info(f"Seeded {i + 1}/{ballot_count} ballots...")
            
            session.commit()
            logger.info(f"Successfully seeded {ballot_count} ballots")
            
        finally:
            session.close()
        
        return tally_line_ids

    def trigger_fast_sync(self, tally_line_ids: List[str]) -> None:
        """Simulate fast-sync by emitting sync signals."""
        logger.info("Triggering fast-sync simulation...")
        
        # In a real system, this would trigger actual sync operations
        # For demo purposes, we'll just simulate the sync completion
        
        # Simulate sync processing time
        time.sleep(0.2)
        
        logger.info(f"Fast-sync completed for {len(tally_line_ids)} tally lines")

    def get_top_winners(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get top 3 winners across all pens."""
        session = self.Session()
        
        try:
            # Get all candidate totals
            candidate_totals = get_totals_by_candidate(session=session)
            
            # Sort by total votes (descending)
            sorted_candidates = sorted(candidate_totals, key=lambda c: c.total_votes, reverse=True)
            
            # Return top winners
            winners = []
            for i, candidate in enumerate(sorted_candidates[:limit]):
                winners.append({
                    "rank": i + 1,
                    "candidate_name": candidate.candidate_name,
                    "party_name": candidate.party_name,
                    "total_votes": candidate.total_votes,
                    "pen_breakdown": candidate.pen_breakdown
                })
            
            return winners
            
        finally:
            session.close()

    def print_winners(self, winners: List[Dict[str, Any]]) -> None:
        """Print winners in a formatted table."""
        print("\n" + "="*80)
        print("🏆 TOP 3 WINNERS - LIVE RESULTS")
        print("="*80)
        
        if not winners:
            print("No votes recorded yet.")
            return
        
        for winner in winners:
            rank_emoji = ["🥇", "🥈", "🥉"][winner["rank"] - 1] if winner["rank"] <= 3 else "🏅"
            
            print(f"\n{rank_emoji} #{winner['rank']}: {winner['candidate_name']}")
            print(f"   Party: {winner['party_name']}")
            print(f"   Total Votes: {winner['total_votes']:,}")
            
            if winner["pen_breakdown"]:
                print("   Pen Breakdown:")
                for pen_name, votes in winner["pen_breakdown"].items():
                    print(f"     • {pen_name}: {votes:,} votes")
        
        print("\n" + "="*80)

    def print_statistics(self) -> None:
        """Print overall election statistics."""
        session = self.Session()
        
        try:
            # Get party totals
            party_totals = get_totals_by_party(session=session)
            
            total_votes = sum(party.total_votes for party in party_totals)
            
            print(f"\n📊 ELECTION STATISTICS")
            print(f"   Total Votes Cast: {total_votes:,}")
            print(f"   Total Parties: {len(party_totals)}")
            print(f"   Active Pens: {len(self.pens)}")
            
            # Show party breakdown
            print(f"\n🎯 PARTY VOTE BREAKDOWN:")
            sorted_parties = sorted(party_totals, key=lambda p: p.total_votes, reverse=True)
            
            for party in sorted_parties:
                percentage = (party.total_votes / total_votes * 100) if total_votes > 0 else 0
                print(f"   • {party.party_name}: {party.total_votes:,} votes ({percentage:.1f}%)")
                
        finally:
            session.close()

    def detect_changes(self, current_winners: List[Dict[str, Any]]) -> bool:
        """Detect if winners have changed since last check."""
        if not self.previous_winners:
            return True
        
        if len(current_winners) != len(self.previous_winners):
            return True
        
        for i, (current, previous) in enumerate(zip(current_winners, self.previous_winners)):
            if (current["candidate_name"] != previous["candidate_name"] or 
                current["total_votes"] != previous["total_votes"]):
                return True
        
        return False

    async def run_demo_loop(self, iterations: int = 5, ballots_per_iteration: int = 200) -> None:
        """Run the main demo loop."""
        print("🚀 Starting Live Results Demo")
        print(f"   Iterations: {iterations}")
        print(f"   Ballots per iteration: {ballots_per_iteration}")
        
        # Setup initial data
        self.setup_demo_data()
        
        for iteration in range(1, iterations + 1):
            print(f"\n🔄 ITERATION {iteration}/{iterations}")
            print("-" * 50)
            
            # Seed random ballots
            start_time = time.time()
            tally_line_ids = self.seed_random_ballots(ballots_per_iteration)
            seed_time = time.time() - start_time
            
            # Trigger fast sync
            sync_start = time.time()
            self.trigger_fast_sync(tally_line_ids)
            sync_time = time.time() - sync_start
            
            # Get current winners
            results_start = time.time()
            current_winners = self.get_top_winners(3)
            results_time = time.time() - results_start
            
            # Check for changes
            has_changes = self.detect_changes(current_winners)
            
            # Print timing information
            print(f"⏱️  Performance Metrics:")
            print(f"   Ballot seeding: {seed_time:.3f}s")
            print(f"   Fast-sync: {sync_time:.3f}s")
            print(f"   Results calculation: {results_time:.3f}s")
            print(f"   Total latency: {(seed_time + sync_time + results_time):.3f}s")
            
            # Print results
            if has_changes:
                print("🔥 RESULTS CHANGED!")
                self.print_winners(current_winners)
                self.print_statistics()
                self.previous_winners = current_winners.copy()
            else:
                print("📊 No changes in top 3 winners")
                print(f"   Current leader: {current_winners[0]['candidate_name']} ({current_winners[0]['total_votes']} votes)")
            
            # Wait before next iteration (except last)
            if iteration < iterations:
                print(f"\n⏳ Waiting 3 seconds before next iteration...")
                await asyncio.sleep(3)
        
        print(f"\n✅ Demo completed after {iterations} iterations!")
        print("📊 Final Results:")
        self.print_winners(self.get_top_winners(3))
        self.print_statistics()

    def cleanup(self) -> None:
        """Clean up demo data."""
        logger.info("Cleaning up demo data...")
        try:
            Path(self.db_url.replace("sqlite:///", "")).unlink(missing_ok=True)
            logger.info("Demo database cleaned up")
        except Exception as e:
            logger.warning(f"Failed to cleanup demo database: {e}")


async def main():
    """Main entry point for the demo script."""
    parser = argparse.ArgumentParser(description="Live Results Demo Script")
    parser.add_argument("--iterations", type=int, default=5, 
                       help="Number of iterations to run (default: 5)")
    parser.add_argument("--ballots", type=int, default=200,
                       help="Ballots per iteration (default: 200)")
    parser.add_argument("--db", type=str, default="sqlite:///demo_live_results.db",
                       help="Database URL (default: sqlite:///demo_live_results.db)")
    parser.add_argument("--cleanup", action="store_true",
                       help="Clean up demo database after completion")
    
    args = parser.parse_args()
    
    # Configure logging
    logger.remove()  # Remove default handler
    logger.add(sys.stdout, 
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
               level="INFO")
    
    demo = LiveResultsDemo(args.db)
    
    try:
        await demo.run_demo_loop(args.iterations, args.ballots)
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    finally:
        if args.cleanup:
            demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 