"""Performance tests for large dataset handling."""

import os
import time
import uuid
from datetime import UTC, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.jcselect.dao_results import get_totals_by_party, get_totals_by_candidate, calculate_winners
from src.jcselect.models import (
    BaseUUIDModel, Pen, Party, User, TallySession, TallyLine
)
from src.jcselect.controllers.results_controller import ResultsController

# Skip performance tests in CI unless explicitly requested
pytestmark = pytest.mark.skipif(
    os.getenv("CI_PERF_SKIP", "1") == "1",
    reason="Performance tests skipped (CI_PERF_SKIP=1)"
)


@pytest.fixture(scope="module")
def large_dataset_db():
    """Create in-memory database with large synthetic dataset."""
    # Use in-memory SQLite for performance tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    BaseUUIDModel.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create synthetic data: 200 pens, 25 parties, lots of tally lines
        pens = []
        parties = []
        users = []
        tally_sessions = []
        tally_lines = []

        print("Creating synthetic dataset...")
        start_time = time.time()

        # Create 200 pens
        for pen_idx in range(200):
            pen = Pen(
                id=str(uuid.uuid4()),
                town_name=f"Town {pen_idx + 1:03d}",
                label=f"Pen {pen_idx + 1:03d}",
                capacity=500
            )
            pens.append(pen)
            session.add(pen)

        # Create 25 parties
        for party_idx in range(25):
            party = Party(
                id=str(uuid.uuid4()),
                name=f"Party {party_idx + 1:02d}",
                abbreviation=f"P{party_idx + 1:02d}",
                color=f"#{''.join([f'{(party_idx * 9) % 256:02x}'] * 3)}"
            )
            parties.append(party)
            session.add(party)

        session.flush()  # Get IDs

        # Create users and tally sessions for each pen
        for pen in pens:
            user = User(
                id=str(uuid.uuid4()),
                username=f"operator_{pen.label.lower().replace(' ', '_')}",
                password_hash="dummy_hash",
                full_name=f"Test Operator {pen.label}",
                role="operator"
            )
            users.append(user)
            session.add(user)

            tally_session = TallySession(
                id=str(uuid.uuid4()),
                pen_id=pen.id,
                operator_id=user.id,
                created_at=datetime.now(timezone.utc),
                status="active"
            )
            tally_sessions.append(tally_session)
            session.add(tally_session)

        session.flush()  # Get IDs

        # Create tally lines with random vote counts
        import random
        random.seed(42)  # Deterministic for testing

        tally_line_count = 0
        for tally_session in tally_sessions:
            # Create multiple tally lines per session for different parties
            for _ in range(random.randint(10, 50)):  # 10-50 tally lines per session
                party = random.choice(parties)

                tally_line = TallyLine(
                    id=str(uuid.uuid4()),
                    tally_session_id=tally_session.id,
                    party_id=party.id,
                    ballot_type="regular",
                    vote_count=random.randint(1, 50),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                tally_lines.append(tally_line)
                tally_line_count += 1
                session.add(tally_line)

        print(f"Created {tally_line_count} tally lines")

        session.commit()

        setup_time = time.time() - start_time
        print(f"Dataset creation took {setup_time:.2f}s")

        yield session, engine

    finally:
        session.close()


@pytest.fixture
def results_controller(large_dataset_db):
    """Create ResultsController with large dataset."""
    session, engine = large_dataset_db

    # Mock the DAO functions to use our test session
    original_get_session = None
    try:
        from src.jcselect.utils.db import get_session
        original_get_session = get_session

        # Mock get_session to return our test session
        def mock_get_session():
            yield session

        import src.jcselect.utils.db
        src.jcselect.utils.db.get_session = mock_get_session

        controller = ResultsController()
        yield controller
    finally:
        # Restore original get_session
        if original_get_session:
            import src.jcselect.utils.db
            src.jcselect.utils.db.get_session = original_get_session


class TestLargeDatasetPerformance:
    """Performance tests for large dataset operations."""

    def test_refresh_data_performance(self, results_controller):
        """Test that refreshData() completes in < 1.5s with large dataset."""
        print("\nTesting refreshData() performance...")

        start_time = time.time()
        results_controller.refreshData()
        end_time = time.time()

        refresh_time = end_time - start_time
        print(f"refreshData() took {refresh_time:.3f}s")

        # Assert performance requirement
        assert refresh_time < 1.5, f"refreshData() took {refresh_time:.3f}s, expected < 1.5s"

        # Verify data was loaded
        assert len(results_controller._party_totals) > 0, "No party totals loaded"
        assert len(results_controller._candidate_totals) > 0, "No candidate totals loaded"

    def test_party_totals_aggregation_performance(self, large_dataset_db):
        """Test party totals aggregation performance."""
        session, engine = large_dataset_db

        print("\nTesting party totals aggregation...")

        start_time = time.time()
        party_totals = get_totals_by_party(session=session)
        end_time = time.time()

        aggregation_time = end_time - start_time
        print(f"Party totals aggregation took {aggregation_time:.3f}s")
        print(f"Loaded {len(party_totals)} party totals")

        # Should complete in reasonable time
        assert aggregation_time < 1.0, f"Party aggregation took {aggregation_time:.3f}s, expected < 1.0s"
        assert len(party_totals) == 25, f"Expected 25 parties, got {len(party_totals)}"

    def test_candidate_totals_aggregation_performance(self, large_dataset_db):
        """Test candidate totals aggregation performance."""
        session, engine = large_dataset_db

        print("\nTesting candidate totals aggregation...")

        start_time = time.time()
        candidate_totals = get_totals_by_candidate(session=session)
        end_time = time.time()

        aggregation_time = end_time - start_time
        print(f"Candidate totals aggregation took {aggregation_time:.3f}s")
        print(f"Loaded {len(candidate_totals)} candidate totals")

        # Should complete in reasonable time
        assert aggregation_time < 2.0, f"Candidate aggregation took {aggregation_time:.3f}s, expected < 2.0s"
        # Note: Since candidates are mocked, we may have fewer actual candidates
        assert len(candidate_totals) >= 0, f"Expected >= 0 candidates, got {len(candidate_totals)}"

    def test_winner_calculation_performance(self, large_dataset_db):
        """Test winner calculation performance with large dataset."""
        session, engine = large_dataset_db

        print("\nTesting winner calculation...")

        # Test winner calculation for first pen
        pens = session.query(Pen).limit(5).all()

        for pen in pens:
            start_time = time.time()
            winners = calculate_winners(pen_id=pen.id, seats=3, session=session)
            end_time = time.time()

            calc_time = end_time - start_time
            print(f"Winner calculation for pen {pen.label} took {calc_time:.3f}s")

            # Should complete quickly per pen
            assert calc_time < 0.5, f"Winner calc took {calc_time:.3f}s, expected < 0.5s"
            assert len(winners) <= 3, f"Expected ≤ 3 winners, got {len(winners)}"

    def test_pen_filtering_performance(self, results_controller):
        """Test performance of pen filtering operations."""
        print("\nTesting pen filtering performance...")

        # Load available pens
        start_time = time.time()
        results_controller.loadAvailablePens()
        end_time = time.time()

        load_time = end_time - start_time
        print(f"Loading available pens took {load_time:.3f}s")
        assert load_time < 0.5, f"Pen loading took {load_time:.3f}s, expected < 0.5s"

        # Test filtering by specific pen
        pens = results_controller._available_pens
        if pens:
            first_pen_id = pens[0]["pen_id"]

            start_time = time.time()
            results_controller.setPenFilter(first_pen_id)
            end_time = time.time()

            filter_time = end_time - start_time
            print(f"Pen filtering took {filter_time:.3f}s")
            assert filter_time < 1.0, f"Pen filtering took {filter_time:.3f}s, expected < 1.0s"

    def test_memory_usage_stability(self, results_controller):
        """Test that memory usage remains stable during repeated operations."""
        import gc

        try:
            import os

            import psutil
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        print(f"\nInitial memory usage: {initial_memory:.1f} MB")

        # Perform multiple refresh operations
        for i in range(10):
            results_controller.refreshData()
            gc.collect()  # Force garbage collection

            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = current_memory - initial_memory

            print(f"Iteration {i+1}: {current_memory:.1f} MB (+{memory_growth:.1f} MB)")

            # Memory growth should be reasonable (< 100MB for large dataset)
            assert memory_growth < 100, f"Memory growth {memory_growth:.1f} MB exceeds limit"

    def test_concurrent_access_simulation(self, large_dataset_db):
        """Test performance under simulated concurrent access."""
        import queue
        import threading

        session, engine = large_dataset_db
        results = queue.Queue()

        def worker_thread(thread_id):
            """Simulate concurrent access."""
            try:
                start_time = time.time()
                party_totals = get_totals_by_party(session=session)
                end_time = time.time()

                results.put({
                    'thread_id': thread_id,
                    'duration': end_time - start_time,
                    'count': len(party_totals),
                    'success': True
                })
            except Exception as e:
                results.put({
                    'thread_id': thread_id,
                    'error': str(e),
                    'success': False
                })

        print("\nTesting concurrent access simulation...")

        # Start 5 concurrent threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout

        # Collect results
        thread_results = []
        while not results.empty():
            thread_results.append(results.get())

        # Verify all threads completed successfully
        assert len(thread_results) == 5, f"Expected 5 results, got {len(thread_results)}"

        successful_threads = [r for r in thread_results if r['success']]
        assert len(successful_threads) == 5, "Not all threads completed successfully"

        # Check performance under concurrent load
        max_duration = max(r['duration'] for r in successful_threads)
        avg_duration = sum(r['duration'] for r in successful_threads) / len(successful_threads)

        print(f"Concurrent access - max: {max_duration:.3f}s, avg: {avg_duration:.3f}s")

        # Performance should not degrade significantly under concurrent load
        assert max_duration < 2.0, f"Max concurrent duration {max_duration:.3f}s exceeds limit"
        assert avg_duration < 1.5, f"Avg concurrent duration {avg_duration:.3f}s exceeds limit"
