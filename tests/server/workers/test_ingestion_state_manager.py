import threading
from unittest.mock import MagicMock, patch

from server.workers.ingestion_state_manager import (
    IngestionPhase,
    IngestionState,
    PhaseProgress,
    SourceIngestionProgressManager,
)


class TestIngestionPhase:
    """Test suite for IngestionPhase enum."""

    def test_ingestion_phase_values(self):
        """Test that all expected phases exist with correct values."""
        assert IngestionPhase.INITIALIZATION.value == "initialization"
        assert IngestionPhase.DOWNLOADING.value == "downloading"
        assert IngestionPhase.TRANSCRIPTION.value == "transcription"
        assert IngestionPhase.EMBEDDING.value == "embedding"
        assert IngestionPhase.STORING.value == "storing"

    def test_ingestion_phase_is_string_enum(self):
        """Test that IngestionPhase is a string enum."""
        assert isinstance(IngestionPhase.INITIALIZATION, str)
        assert IngestionPhase.INITIALIZATION == "initialization"


class TestPhaseProgress:
    """Test suite for PhaseProgress class."""

    def test_init_default(self):
        """Test default initialization."""
        progress = PhaseProgress()
        assert progress.current == 0
        assert progress.total is None
        assert hasattr(progress, "_lock")

    def test_init_with_values(self):
        """Test initialization with values."""
        progress = PhaseProgress(current=5, total=10)
        assert progress.current == 5
        assert progress.total == 10

    def test_percentage_with_total(self):
        """Test percentage calculation when total is set."""
        progress = PhaseProgress(current=25, total=100)
        assert progress.percentage == 25.0

        progress.current = 50
        assert progress.percentage == 50.0

    def test_percentage_without_total(self):
        """Test percentage returns None when total is not set."""
        progress = PhaseProgress(current=10)
        assert progress.percentage is None

    def test_percentage_with_zero_total(self):
        """Test percentage returns None when total is zero."""
        progress = PhaseProgress(current=10, total=0)
        assert progress.percentage is None

    def test_set_progress(self):
        """Test setting progress value."""
        progress = PhaseProgress()
        progress.set_progress(42)
        assert progress.current == 42

    def test_increment(self):
        """Test incrementing progress."""
        progress = PhaseProgress(current=10)
        progress.increment()
        assert progress.current == 11

        progress.increment(5)
        assert progress.current == 16

    def test_set_total(self):
        """Test setting total value."""
        progress = PhaseProgress()
        progress.set_total(100)
        assert progress.total == 100

    def test_thread_safety(self):
        """Test that operations are thread-safe."""
        progress = PhaseProgress(current=0, total=1000)
        errors = []

        def increment_many():
            try:
                for _ in range(100):
                    progress.increment()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=increment_many) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert progress.current == 1000  # 10 threads * 100 increments


class TestIngestionState:
    """Test suite for IngestionState class."""

    def test_init_minimal(self):
        """Test minimal initialization."""
        state = IngestionState("test-source-id")
        assert state.data_source_id == "test-source-id"
        assert state.current_phase is None
        assert state.phase_progress == {}
        assert state.success_callback is None
        assert state.failure_callback is None
        assert hasattr(state, "_lock")

    def test_init_with_callbacks(self):
        """Test initialization with callbacks."""
        success_cb = MagicMock()
        failure_cb = MagicMock()
        state = IngestionState("test-source-id", success_cb, failure_cb)
        assert state.success_callback == success_cb
        assert state.failure_callback == failure_cb

    def test_get_or_create_phase_new(self):
        """Test getting or creating a new phase."""
        state = IngestionState("test-source-id")
        progress = state.get_or_create_phase(IngestionPhase.DOWNLOADING)

        assert isinstance(progress, PhaseProgress)
        assert IngestionPhase.DOWNLOADING in state.phase_progress
        assert state.phase_progress[IngestionPhase.DOWNLOADING] == progress
        assert state.current_phase == IngestionPhase.DOWNLOADING

    def test_get_or_create_phase_existing(self):
        """Test getting an existing phase."""
        state = IngestionState("test-source-id")
        progress1 = state.get_or_create_phase(IngestionPhase.DOWNLOADING)
        progress1.set_progress(50)

        progress2 = state.get_or_create_phase(IngestionPhase.DOWNLOADING, is_current_phase=False)
        assert progress2 == progress1
        assert progress2.current == 50

    def test_get_or_create_phase_not_current(self):
        """Test creating phase without setting as current."""
        state = IngestionState("test-source-id")
        state.current_phase = IngestionPhase.EMBEDDING

        progress = state.get_or_create_phase(IngestionPhase.DOWNLOADING, is_current_phase=False)
        assert isinstance(progress, PhaseProgress)
        assert state.current_phase == IngestionPhase.EMBEDDING  # Should not change

    def test_to_dict(self):
        """Test converting state to dictionary."""
        state = IngestionState("test-source-id")

        # Add some phases
        download_progress = state.get_or_create_phase(IngestionPhase.DOWNLOADING)
        download_progress.set_total(100)
        download_progress.set_progress(50)

        embed_progress = state.get_or_create_phase(IngestionPhase.EMBEDDING)
        embed_progress.set_total(200)
        embed_progress.set_progress(150)

        result = state.to_dict()

        assert result["data_source_id"] == "test-source-id"
        assert len(result["phase_progresses"]) == 2

        # Find the phases in the result
        phases_by_name = {p["phase"]: p for p in result["phase_progresses"]}

        assert phases_by_name["downloading"]["percentage"] == 50.0
        assert phases_by_name["downloading"]["is_current_phase"] is False

        assert phases_by_name["embedding"]["percentage"] == 75.0
        assert phases_by_name["embedding"]["is_current_phase"] is True


class TestSourceIngestionProgressManager:
    """Test suite for SourceIngestionProgressManager class."""

    def test_init(self):
        """Test initialization."""
        manager = SourceIngestionProgressManager()
        assert hasattr(manager, "_states")
        assert manager._states == {}

    def test_create_state(self):
        """Test creating a new state."""
        manager = SourceIngestionProgressManager()
        success_cb = MagicMock()
        failure_cb = MagicMock()

        state = manager.create_state("source1", success_cb, failure_cb)

        assert isinstance(state, IngestionState)
        assert state.data_source_id == "source1"
        assert state.success_callback == success_cb
        assert state.failure_callback == failure_cb
        assert "source1" in manager._states

    def test_add_phase_new_source(self):
        """Test adding phase to a new source."""
        manager = SourceIngestionProgressManager()

        with patch("server.workers.ingestion_state_manager.logger") as mock_logger:
            state = manager.add_phase("new-source", IngestionPhase.INITIALIZATION, total=5)

            assert isinstance(state, IngestionState)
            assert "new-source" in manager._states
            assert state.current_phase == IngestionPhase.INITIALIZATION
            mock_logger.debug.assert_called()

            # Check total was set
            progress = state.phase_progress[IngestionPhase.INITIALIZATION]
            assert progress.total == 5

    def test_add_phase_existing_source(self):
        """Test adding phase to an existing source."""
        manager = SourceIngestionProgressManager()
        manager.create_state("existing-source")

        state = manager.add_phase("existing-source", IngestionPhase.EMBEDDING, total=100)

        assert state.current_phase == IngestionPhase.EMBEDDING
        progress = state.phase_progress[IngestionPhase.EMBEDDING]
        assert progress.total == 100

    def test_get_state_existing(self):
        """Test getting an existing state."""
        manager = SourceIngestionProgressManager()
        created_state = manager.create_state("test-source")

        retrieved_state = manager.get_state("test-source")
        assert retrieved_state == created_state

    def test_get_state_nonexistent(self):
        """Test getting a non-existent state."""
        manager = SourceIngestionProgressManager()

        with patch("server.workers.ingestion_state_manager.logger") as mock_logger:
            state = manager.get_state("nonexistent")
            assert state is None
            mock_logger.warning.assert_called_once_with("Ingestion state for data source nonexistent not found")

    def test_set_phase_total(self):
        """Test setting phase total."""
        manager = SourceIngestionProgressManager()
        manager.create_state("test-source")
        manager.add_phase("test-source", IngestionPhase.DOWNLOADING)

        with patch("server.workers.ingestion_state_manager.logger") as mock_logger:
            manager.set_phase_total("test-source", IngestionPhase.DOWNLOADING, 50)

            state = manager.get_state("test-source")
            progress = state.phase_progress[IngestionPhase.DOWNLOADING]
            assert progress.total == 50
            mock_logger.debug.assert_called()

    def test_set_phase_total_nonexistent_source(self):
        """Test setting phase total for non-existent source."""
        manager = SourceIngestionProgressManager()
        result = manager.set_phase_total("nonexistent", IngestionPhase.DOWNLOADING, 50)
        assert result is None

    def test_increment_phase_progress(self):
        """Test incrementing phase progress."""
        manager = SourceIngestionProgressManager()
        manager.create_state("test-source")
        manager.add_phase("test-source", IngestionPhase.EMBEDDING)

        with patch("server.workers.ingestion_state_manager.logger") as mock_logger:
            manager.increment_phase_progress("test-source", IngestionPhase.EMBEDDING, 5)

            state = manager.get_state("test-source")
            progress = state.phase_progress[IngestionPhase.EMBEDDING]
            assert progress.current == 5
            mock_logger.debug.assert_called()

    def test_set_phase_progress(self):
        """Test setting phase progress."""
        manager = SourceIngestionProgressManager()
        manager.create_state("test-source")
        manager.add_phase("test-source", IngestionPhase.TRANSCRIPTION)

        with patch("server.workers.ingestion_state_manager.logger") as mock_logger:
            manager.set_phase_progress("test-source", IngestionPhase.TRANSCRIPTION, 75)

            state = manager.get_state("test-source")
            progress = state.phase_progress[IngestionPhase.TRANSCRIPTION]
            assert progress.current == 75
            mock_logger.debug.assert_called()

    def test_get_phase_percentage_current_phase(self):
        """Test getting percentage for current phase."""
        manager = SourceIngestionProgressManager()
        manager.create_state("test-source")
        manager.add_phase("test-source", IngestionPhase.STORING, total=100)
        manager.set_phase_progress("test-source", IngestionPhase.STORING, 25)

        percentage = manager.get_phase_percentage("test-source")
        assert percentage == 25.0

    def test_get_phase_percentage_specific_phase(self):
        """Test getting percentage for specific phase."""
        manager = SourceIngestionProgressManager()
        manager.create_state("test-source")
        manager.add_phase("test-source", IngestionPhase.STORING, total=100)
        manager.set_phase_progress("test-source", IngestionPhase.STORING, 75)

        # Add another phase as current
        manager.add_phase("test-source", IngestionPhase.EMBEDDING)

        percentage = manager.get_phase_percentage("test-source", IngestionPhase.STORING)
        assert percentage == 75.0

    def test_get_phase_percentage_no_current_phase(self):
        """Test getting percentage when no current phase."""
        manager = SourceIngestionProgressManager()
        manager.create_state("test-source")

        percentage = manager.get_phase_percentage("test-source")
        assert percentage is None

    def test_get_phase_percentage_nonexistent_source(self):
        """Test getting percentage for non-existent source."""
        manager = SourceIngestionProgressManager()
        percentage = manager.get_phase_percentage("nonexistent")
        assert percentage is None

    def test_remove_source_state(self):
        """Test removing a source state."""
        manager = SourceIngestionProgressManager()
        manager.create_state("test-source")

        with patch("server.workers.ingestion_state_manager.logger") as mock_logger:
            manager.remove_source_state("test-source")
            assert "test-source" not in manager._states
            mock_logger.warning.assert_not_called()

    def test_remove_source_state_nonexistent(self):
        """Test removing non-existent source state."""
        manager = SourceIngestionProgressManager()

        with patch("server.workers.ingestion_state_manager.logger") as mock_logger:
            manager.remove_source_state("nonexistent")
            mock_logger.warning.assert_called_once_with("Ingestion state for data source nonexistent not found")

    def test_mark_as_completed(self):
        """Test marking source as completed."""
        manager = SourceIngestionProgressManager()
        success_cb = MagicMock()
        manager.create_state("test-source", success_callback=success_cb)

        manager.mark_as_completed("test-source")

        success_cb.assert_called_once()
        assert "test-source" not in manager._states

    def test_mark_as_completed_no_callback(self):
        """Test marking as completed without callback."""
        manager = SourceIngestionProgressManager()
        manager.create_state("test-source")

        manager.mark_as_completed("test-source")
        assert "test-source" not in manager._states

    def test_mark_as_completed_nonexistent(self):
        """Test marking non-existent source as completed."""
        manager = SourceIngestionProgressManager()
        result = manager.mark_as_completed("nonexistent")
        assert result is None

    def test_mark_as_failed(self):
        """Test marking source as failed."""
        manager = SourceIngestionProgressManager()
        failure_cb = MagicMock()
        manager.create_state("test-source", failure_callback=failure_cb)

        manager.mark_as_failed("test-source")

        failure_cb.assert_called_once()
        assert "test-source" not in manager._states

    def test_mark_as_failed_no_callback(self):
        """Test marking as failed without callback."""
        manager = SourceIngestionProgressManager()
        manager.create_state("test-source")

        manager.mark_as_failed("test-source")
        assert "test-source" not in manager._states

    def test_mark_as_failed_nonexistent(self):
        """Test marking non-existent source as failed."""
        manager = SourceIngestionProgressManager()
        result = manager.mark_as_failed("nonexistent")
        assert result is None

    def test_multiple_sources(self):
        """Test managing multiple sources simultaneously."""
        manager = SourceIngestionProgressManager()

        # Create multiple sources
        manager.create_state("source1")
        manager.create_state("source2")
        manager.create_state("source3")

        # Add phases to different sources
        manager.add_phase("source1", IngestionPhase.DOWNLOADING, total=100)
        manager.add_phase("source2", IngestionPhase.EMBEDDING, total=200)
        manager.add_phase("source3", IngestionPhase.STORING, total=50)

        # Update progress
        manager.set_phase_progress("source1", IngestionPhase.DOWNLOADING, 50)
        manager.set_phase_progress("source2", IngestionPhase.EMBEDDING, 100)
        manager.set_phase_progress("source3", IngestionPhase.STORING, 25)

        # Verify each source independently
        assert manager.get_phase_percentage("source1") == 50.0
        assert manager.get_phase_percentage("source2") == 50.0
        assert manager.get_phase_percentage("source3") == 50.0

        # Remove one source
        manager.mark_as_completed("source2")
        assert "source2" not in manager._states
        assert "source1" in manager._states
        assert "source3" in manager._states
