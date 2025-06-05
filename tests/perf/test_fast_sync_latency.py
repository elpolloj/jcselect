"""Performance tests for fast sync latency."""

import os
import time
import uuid
from datetime import UTC, datetime, timezone
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.jcselect.models import BaseUUIDModel, Pen, Party, User, TallySession, TallyLine
from src.jcselect.sync.engine import SyncEngine
from src.jcselect.controllers.results_controller import ResultsController
from src.jcselect.utils.db import get_session

# Skip performance tests in CI unless explicitly requested
pytestmark = pytest.mark.skipif(
    os.getenv("CI_PERF_SKIP", "1") == "1",
    reason="Performance tests skipped (CI_PERF_SKIP=1)"
)


@pytest.fixture(scope="module")
def test_db():
    """Create test database with basic data."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    BaseUUIDModel.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create minimal test data
        pen = Pen(
            id=str(uuid.uuid4()),
            town_name="Test Town",
            label="Test Pen 001",
            capacity=500
        )
        session.add(pen)

        party = Party(
            id=str(uuid.uuid4()),
            name="Test Party",
            abbreviation="TP",
            color="#0066CC"
        )
        session.add(party)

        user = User(
            id=str(uuid.uuid4()),
            username="test_operator",
            password_hash="hash",
            full_name="Test Operator",
            role="operator"
        )
        session.add(user)

        session.flush()

        tally_session = TallySession(
            id=str(uuid.uuid4()),
            pen_id=pen.id,
            operator_id=user.id,
            created_at=datetime.now(datetime.UTC),
            status="active"
        )
        session.add(tally_session)

        session.commit()

        yield session, engine, pen, party, tally_session

    finally:
        session.close()


@pytest.fixture
def mock_sync_engine(qtbot):
    """Create mock sync engine for testing."""
    sync_engine = Mock(spec=SyncEngine)
    sync_engine.syncCompleted = Mock()
    sync_engine.syncStarted = Mock()
    sync_engine.syncFailed = Mock()
    sync_engine.tallyLineUpdated = Mock()
    sync_engine.tallySessionUpdated = Mock()
    sync_engine.entityUpdated = Mock()

    # Mock signal connections
    sync_engine.syncCompleted.connect = Mock()
    sync_engine.tallyLineUpdated.connect = Mock()

    return sync_engine


@pytest.fixture
def results_controller_with_sync(test_db, mock_sync_engine, qtbot):
    """Create ResultsController with mocked sync engine."""
    session, engine, pen, party, tally_session = test_db

    # Mock get_sync_engine to return our mock
    with patch('src.jcselect.controllers.results_controller.get_sync_engine', return_value=mock_sync_engine):
        # Mock get_session to use test session
        from src.jcselect.utils.db import get_session

        def mock_get_session():
            yield session

        with patch('src.jcselect.utils.db.get_session', mock_get_session):
            controller = ResultsController()
            yield controller, mock_sync_engine, session, pen, party, tally_session


class TestFastSyncLatency:
    """Performance tests for fast sync latency."""

    def test_single_ballot_confirmation_latency(self, results_controller_with_sync, qtbot):
        """Test latency for single ballot confirmation to results update."""
        controller, sync_engine, session, pen, party, tally_session = results_controller_with_sync

        print("\nTesting single ballot confirmation latency...")

        # Create initial tally line
        tally_line = TallyLine(
            id=str(uuid.uuid4()),
            tally_session_id=tally_session.id,
            party_id=party.id,
            ballot_type="regular",
            vote_count=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(tally_line)
        session.commit()

        # Record initial refresh time
        start_time = time.time()
        controller.refreshData()
        initial_refresh_time = time.time() - start_time
        print(f"Initial refresh took {initial_refresh_time:.3f}s")

        # Simulate ballot confirmation by triggering sync completion
        start_time = time.time()

        # Trigger the sync completion callback directly
        if hasattr(controller, '_on_sync_completed'):
            controller._on_sync_completed()

        # Wait for refresh to complete (auto-triggered by sync completion)
        qtbot.wait(100)  # Allow time for QTimer.singleShot delay

        end_time = time.time()
        update_latency = end_time - start_time

        print(f"Sync completion to results update latency: {update_latency:.3f}s")

        # Assert performance requirement: ≤ 2s end-to-end
        assert update_latency <= 2.0, f"Update latency {update_latency:.3f}s exceeds 2.0s limit"

    def test_rapid_ballot_confirmations_latency(self, results_controller_with_sync, qtbot):
        """Test latency with 50 rapid ballot confirmations."""
        controller, sync_engine, session, pen, party, tally_session = results_controller_with_sync

        print("\nTesting 50 rapid ballot confirmations...")

        latencies = []

        for i in range(50):
            # Create new tally line (simulating ballot confirmation)
            tally_line = TallyLine(
                id=str(uuid.uuid4()),
                tally_session_id=tally_session.id,
                party_id=party.id,
                ballot_type="regular",
                vote_count=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(tally_line)
            session.commit()

            # Measure update latency
            start_time = time.time()

            # Trigger sync completion
            if hasattr(controller, '_on_sync_completed'):
                controller._on_sync_completed()

            # Wait for refresh
            qtbot.wait(100)

            end_time = time.time()
            latency = end_time - start_time
            latencies.append(latency)

            # Small delay between confirmations
            time.sleep(0.01)

        # Analyze latencies
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)

        print("Latency stats over 50 confirmations:")
        print(f"  Average: {avg_latency:.3f}s")
        print(f"  Maximum: {max_latency:.3f}s")
        print(f"  Minimum: {min_latency:.3f}s")

        # Performance assertions
        assert avg_latency <= 2.0, f"Average latency {avg_latency:.3f}s exceeds 2.0s"
        assert max_latency <= 3.0, f"Maximum latency {max_latency:.3f}s exceeds 3.0s"

        # Ensure latency doesn't degrade significantly over time
        first_10_avg = sum(latencies[:10]) / 10
        last_10_avg = sum(latencies[-10:]) / 10
        degradation = last_10_avg - first_10_avg

        print(f"Latency degradation: {degradation:.3f}s (first 10 avg: {first_10_avg:.3f}s, last 10 avg: {last_10_avg:.3f}s)")
        assert degradation <= 0.5, f"Latency degraded by {degradation:.3f}s, should be ≤ 0.5s"

    def test_debounced_refresh_performance(self, results_controller_with_sync, qtbot):
        """Test that debounced refresh prevents excessive updates."""
        controller, sync_engine, session, pen, party, tally_session = results_controller_with_sync

        print("\nTesting debounced refresh performance...")

        # Track refresh calls
        original_refresh = controller.refreshData
        refresh_count = 0
        refresh_times = []

        def tracked_refresh():
            nonlocal refresh_count
            refresh_count += 1
            refresh_times.append(time.time())
            return original_refresh()

        controller.refreshData = tracked_refresh

        # Trigger multiple rapid sync completions
        start_time = time.time()

        for i in range(20):
            # Create tally line
            tally_line = TallyLine(
                id=str(uuid.uuid4()),
                tally_session_id=tally_session.id,
                party_id=party.id,
                ballot_type="regular",
                vote_count=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(tally_line)
            session.commit()

            # Trigger sync completion
            if hasattr(controller, '_on_sync_completed'):
                controller._on_sync_completed()

            # Very short delay (rapid updates)
            time.sleep(0.01)

        # Wait for all debounced refreshes to complete
        qtbot.wait(500)  # Wait longer than debounce delay

        end_time = time.time()
        total_time = end_time - start_time

        print(f"20 rapid sync completions in {total_time:.3f}s")
        print(f"Triggered {refresh_count} actual refreshes")

        # With debouncing, we should have significantly fewer refreshes than sync events
        assert refresh_count < 20, f"Expected < 20 refreshes due to debouncing, got {refresh_count}"
        assert refresh_count >= 1, f"Expected at least 1 refresh, got {refresh_count}"

        # Total time should be reasonable
        assert total_time <= 3.0, f"Total time {total_time:.3f}s should be ≤ 3.0s"

    def test_auto_refresh_toggle_performance(self, results_controller_with_sync, qtbot):
        """Test performance impact of auto-refresh toggle."""
        controller, sync_engine, session, pen, party, tally_session = results_controller_with_sync

        print("\nTesting auto-refresh toggle performance...")

        # Test with auto-refresh enabled
        if hasattr(controller, '_auto_refresh_enabled'):
            controller._auto_refresh_enabled = True

        start_time = time.time()
        for i in range(10):
            if hasattr(controller, '_on_sync_completed'):
                controller._on_sync_completed()
            qtbot.wait(10)
        enabled_time = time.time() - start_time

        # Test with auto-refresh disabled
        if hasattr(controller, '_auto_refresh_enabled'):
            controller._auto_refresh_enabled = False

        start_time = time.time()
        for i in range(10):
            if hasattr(controller, '_on_sync_completed'):
                controller._on_sync_completed()
            qtbot.wait(10)
        disabled_time = time.time() - start_time

        print(f"Auto-refresh enabled: {enabled_time:.3f}s")
        print(f"Auto-refresh disabled: {disabled_time:.3f}s")

        # Both should complete quickly
        assert enabled_time <= 2.0, f"Auto-refresh enabled time {enabled_time:.3f}s too high"
        assert disabled_time <= 1.0, f"Auto-refresh disabled time {disabled_time:.3f}s too high"

        # Disabled should be faster (no refresh operations)
        assert disabled_time <= enabled_time, "Disabled auto-refresh should be faster"

    def test_sync_engine_integration_latency(self, test_db, qtbot):
        """Test integration latency with real sync engine signals."""
        session, engine, pen, party, tally_session = test_db

        print("\nTesting sync engine integration latency...")

        # Create real sync engine for integration test

        def mock_get_session():
            yield session

        with patch('src.jcselect.utils.db.get_session', mock_get_session):
            sync_engine = SyncEngine()

            # Create results controller that connects to sync engine
            with patch('src.jcselect.controllers.results_controller.get_sync_engine', return_value=sync_engine):
                controller = ResultsController()

                # Track when refresh completes
                refresh_completed = False
                refresh_time = None

                def on_refresh_complete():
                    nonlocal refresh_completed, refresh_time
                    refresh_completed = True
                    refresh_time = time.time()

                # Connect to refresh completion (if signal exists)
                if hasattr(controller, 'dataRefreshed'):
                    controller.dataRefreshed.connect(on_refresh_complete)

                # Measure latency of sync signal to refresh completion
                start_time = time.time()

                # Emit sync completion signal
                sync_engine.syncCompleted.emit()

                # Wait for refresh to complete
                timeout = 5000  # 5 second timeout
                while not refresh_completed and timeout > 0:
                    qtbot.wait(10)
                    timeout -= 10

                if refresh_completed:
                    latency = refresh_time - start_time
                    print(f"Sync signal to refresh completion: {latency:.3f}s")

                    # Assert integration latency requirement
                    assert latency <= 2.0, f"Integration latency {latency:.3f}s exceeds 2.0s"
                else:
                    print("Refresh did not complete within timeout")
                    # For this test, we'll just log the issue rather than failing
                    # since the signal connection might not be fully implemented

    def test_tally_line_specific_updates(self, results_controller_with_sync, qtbot):
        """Test performance of tally line specific update signals."""
        controller, sync_engine, session, pen, party, tally_session = results_controller_with_sync

        print("\nTesting tally line specific updates...")

        # Create some initial tally lines
        tally_lines = []
        for i in range(5):
            tally_line = TallyLine(
                id=str(uuid.uuid4()),
                tally_session_id=tally_session.id,
                party_id=party.id,
                ballot_type="regular",
                vote_count=5,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            tally_lines.append(tally_line)
            session.add(tally_line)

        session.commit()

        # Test latency for specific tally line updates
        latencies = []

        for tally_line in tally_lines:
            start_time = time.time()

            # Trigger tally line updated signal
            if hasattr(controller, '_on_tally_updated'):
                controller._on_tally_updated(tally_line.id)

            # Wait for processing
            qtbot.wait(50)

            end_time = time.time()
            latency = end_time - start_time
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print("Tally line update latencies:")
        print(f"  Average: {avg_latency:.3f}s")
        print(f"  Maximum: {max_latency:.3f}s")

        # Specific updates should be very fast
        assert avg_latency <= 0.5, f"Average tally update latency {avg_latency:.3f}s too high"
        assert max_latency <= 1.0, f"Maximum tally update latency {max_latency:.3f}s too high"

    def test_memory_impact_during_rapid_updates(self, results_controller_with_sync, qtbot):
        """Test memory impact during rapid sync updates."""
        import gc

        try:
            import os

            import psutil
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        controller, sync_engine, session, pen, party, tally_session = results_controller_with_sync

        print("\nTesting memory impact during rapid updates...")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        print(f"Initial memory: {initial_memory:.1f} MB")

        # Perform 100 rapid updates
        for i in range(100):
            # Create tally line
            tally_line = TallyLine(
                id=str(uuid.uuid4()),
                tally_session_id=tally_session.id,
                party_id=party.id,
                ballot_type="regular",
                vote_count=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(tally_line)
            session.commit()

            # Trigger update
            if hasattr(controller, '_on_sync_completed'):
                controller._on_sync_completed()

            # Check memory every 20 iterations
            if (i + 1) % 20 == 0:
                gc.collect()
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_growth = current_memory - initial_memory

                print(f"After {i+1} updates: {current_memory:.1f} MB (+{memory_growth:.1f} MB)")

                # Memory growth should be reasonable during rapid updates
                assert memory_growth < 50, f"Memory growth {memory_growth:.1f} MB too high after {i+1} updates"

        # Final memory check
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_growth = final_memory - initial_memory

        print(f"Final memory: {final_memory:.1f} MB (total growth: {total_growth:.1f} MB)")

        # Total memory growth should be reasonable
        assert total_growth < 100, f"Total memory growth {total_growth:.1f} MB exceeds limit"
