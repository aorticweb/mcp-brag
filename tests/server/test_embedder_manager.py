"""Tests for the EmbedderThreadManager."""

import time
from datetime import timedelta

import pytest

from embedder.constants import ASYNC_QUEUE_MAX_SIZE
from embedder.read_write.bulk_queue import BulkQueue
from embedder.text import TextInput
from server.constants import EMBEDDER_IDLE_TIMEOUT
from server.thread_managers.embedder_manager import EmbedderThreadManager
from server.workers.ingestion_state_manager import SourceIngestionProgressManager


class TestEmbedderThreadManager:
    """Test cases for EmbedderThreadManager."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test queues
        self.read_queue = BulkQueue(maxsize=ASYNC_QUEUE_MAX_SIZE.value)
        self.write_queue = BulkQueue(maxsize=ASYNC_QUEUE_MAX_SIZE.value)

        # Save original timeout and set shorter one for testing
        self.original_timeout = EMBEDDER_IDLE_TIMEOUT._value
        EMBEDDER_IDLE_TIMEOUT._value = timedelta(seconds=3)

        # Create ingestion state manager
        self.ingestion_state_manager = SourceIngestionProgressManager()

        # Create manager
        self.manager = EmbedderThreadManager(self.read_queue, self.write_queue, self.ingestion_state_manager)

    def teardown_method(self):
        """Clean up after tests."""
        # Stop the thread if running
        if self.manager:
            self.manager.stop()

        # Restore original timeout
        EMBEDDER_IDLE_TIMEOUT._value = self.original_timeout

    def test_thread_starts_on_ensure_running(self):
        """Test that thread starts when ensure_running is called."""
        assert not self.manager.is_running()

        self.manager.ensure_running()

        assert self.manager.is_running()

    def test_thread_stays_alive_while_processing(self):
        """Test that thread stays alive while there's work in the queue."""
        self.manager.ensure_running()
        assert self.manager.is_running()

        # Add work to queue
        test_input = TextInput("Test text", metadata={"source": "test", "source_type": "test"})
        self.read_queue.put_nowait(test_input)

        # Wait a bit and verify thread is still alive
        time.sleep(1)
        assert self.manager.is_running()

    def test_thread_terminates_after_idle_timeout(self):
        """Test that thread terminates after being idle for the timeout period."""
        self.manager.ensure_running()
        assert self.manager.is_running()

        # Wait for timeout plus buffer
        time.sleep(EMBEDDER_IDLE_TIMEOUT._value.seconds + 1)

        assert not self.manager.is_running()

    def test_thread_restarts_when_needed(self):
        """Test that thread can be restarted after termination."""
        # Start thread
        self.manager.ensure_running()
        assert self.manager.is_running()

        # Let it timeout
        time.sleep(EMBEDDER_IDLE_TIMEOUT._value.seconds + 1)
        assert not self.manager.is_running()

        # Restart
        self.manager.ensure_running()
        assert self.manager.is_running()

    def test_ensure_running_is_idempotent(self):
        """Test that calling ensure_running multiple times is safe."""
        self.manager.ensure_running()
        thread1 = self.manager._thread

        # Call again - should not create new thread
        self.manager.ensure_running()
        thread2 = self.manager._thread

        assert thread1 is thread2
        assert self.manager.is_running()

    def test_stop_terminates_thread(self):
        """Test that stop() terminates the thread."""
        self.manager.ensure_running()
        assert self.manager.is_running()

        self.manager.stop()

        # Give thread time to stop
        time.sleep(0.5)
        assert not self.manager.is_running()

    def test_thread_processes_multiple_items(self):
        """Test that thread processes multiple items from queue."""
        self.manager.ensure_running()

        # Add multiple items
        for i in range(5):
            test_input = TextInput(f"Test text {i}", metadata={"source": f"test_{i}", "source_type": "test"})
            self.read_queue.put_nowait(test_input)

        # Wait for processing
        time.sleep(2)

        # Thread should still be running
        assert self.manager.is_running()

        # Queue should be processed (embedder will move items to write queue)
        assert self.read_queue.qsize() == 0

    @pytest.mark.parametrize("timeout_seconds", [2, 4, 6])
    def test_configurable_timeout(self, timeout_seconds):
        """Test that timeout is configurable."""
        EMBEDDER_IDLE_TIMEOUT._value = timedelta(seconds=timeout_seconds)

        manager = EmbedderThreadManager(self.read_queue, self.write_queue, self.ingestion_state_manager)
        manager.ensure_running()

        # Should be running before timeout
        time.sleep(timeout_seconds - 1)
        assert manager.is_running()

        # Should terminate after timeout
        time.sleep(2)
        assert not manager.is_running()

        # Clean up
        manager.stop()
