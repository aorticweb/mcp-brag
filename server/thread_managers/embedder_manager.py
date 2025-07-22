import time

from common.log import get_logger
from embedder.embed import get_embedder
from embedder.read_write.bulk_queue import BulkQueue, BulkQueueReadWriter
from server.constants import EMBEDDER_IDLE_TIMEOUT
from server.thread_managers.interface import SelfTerminatingThreadManager
from server.workers.ingestion_state_manager import SourceIngestionProgressManager

logger = get_logger(__name__)


class EmbedderThreadManager(SelfTerminatingThreadManager):
    def __init__(
        self, read_queue: BulkQueue, write_queue: BulkQueue, ingestion_state_manager: SourceIngestionProgressManager
    ):
        """Initialize the embedder thread manager.

        Args:
            read_queue: Queue for reading text inputs to embed
            write_queue: Queue for writing embedded outputs
        """
        self._read_queue = read_queue
        self._write_queue = write_queue
        self._ingestion_state_manager = ingestion_state_manager
        super().__init__(activity_timeout=EMBEDDER_IDLE_TIMEOUT.value)

    def run(self):
        """Run the embedder in a loop until stopped or idle timeout."""
        logger.debug("Starting embedder thread")

        # Create embedder instance for this thread
        transport = BulkQueueReadWriter(self._read_queue, self._write_queue)
        embedder = get_embedder(transport, ingestion_state_manager=self._ingestion_state_manager)

        while not self._should_stop:
            # Check if there's data in the queue
            if self._read_queue.qsize() > 0:
                self.mark_as_active()
                embedder.iter()
            else:
                # No data, check if we should terminate
                if self.should_terminate_due_to_idle():
                    break
                time.sleep(0.3)

        # Free resources before exiting
        embedder._vectorizer.free()
        logger.info("Embedder thread terminated")

    def name(self) -> str:
        """
        Get the display name of this thread manager

        Returns:
            str: The descriptive name of this thread manager
        """
        return "Embedder Thread Manager"
