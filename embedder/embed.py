"""Text embedding processing module.

This module provides a high-level interface for processing text batches through
vectorization pipelines. It coordinates between transport layers and vectorization
engines to efficiently process text inputs at scale.

The module supports configurable vectorizers and bulk queue-based transport
for optimal performance in multi-threaded environments.
"""

from typing import Optional

from common.log import get_logger
from embedder.constants import VECTORIZER_MODEL_PATH
from embedder.read_write.bulk_queue import BulkQueueReadWriter
from embedder.text import TextBatch
from embedder.vectorizer import Vectorizer
from embedder.vectorizer.sentence import SentenceTransformerVectorizer
from server.workers.ingestion_state_manager import (
    IngestionPhase,
    SourceIngestionProgressManager,
)

logger = get_logger(__name__)


class Embedder:
    __slots__ = "_transport", "_vectorizer", "_ingestion_state_manager"

    """Main embedder class for processing text batches through vectorization.

    The Embedder coordinates between a transport layer (for reading/writing batches)
    and a vectorizer (for converting text to embeddings). It processes batches
    atomically to ensure consistency and optimal performance.

    This class is designed to be run in a continuous loop, processing batches
    as they become available. It handles empty batches gracefully and provides
    detailed logging for monitoring.

    Attributes:
        _transport: Interface for reading input batches and writing output batches
        _vectorizer: Engine for converting text to vector embeddings
    """

    def __init__(
        self,
        transport: BulkQueueReadWriter,
        vectorizer: Vectorizer,
        ingestion_state_manager: Optional[SourceIngestionProgressManager] = None,
    ) -> None:
        """Initialize the embedder with transport and vectorization components.

        Args:
            transport: Transport layer for reading input and writing output batches
            vectorizer: Vectorization engine for converting text to embeddings

        Raises:
            TypeError: If transport or vectorizer are not of expected types
        """
        if not isinstance(transport, BulkQueueReadWriter):
            raise TypeError(f"Expected BulkQueueReadWriter, got {type(transport)}")
        if not isinstance(vectorizer, Vectorizer):
            raise TypeError(f"Expected Vectorizer, got {type(vectorizer)}")

        self._transport = transport
        self._vectorizer = vectorizer
        self._ingestion_state_manager = ingestion_state_manager
        logger.info(f"Embedder initialized with vectorizer: {type(vectorizer).__name__}")

    def iter(self) -> None:
        """Process one batch iteration from the transport queue.

        This method reads a batch from the transport, vectorizes the text inputs,
        and writes the results back to the transport. It handles empty batches
        gracefully by returning early.

        The method processes batches atomically - either the entire batch is
        processed successfully or none of it is written to the output queue.

        Raises:
            Exception: May raise exceptions from the vectorizer or transport layers.
                      Callers should handle these appropriately for their use case.
        """
        batch = self._transport.read()

        # Early return for empty batches to avoid unnecessary processing
        if len(batch) == 0:
            return

        logger.debug(f"Processing batch of {len(batch)} text inputs")

        try:
            # Vectorize the batch in-place
            self._vectorizer.vectorize(batch)

            if self._ingestion_state_manager is not None:
                for source_id, count in batch.count_by_source_id().items():
                    if source_id is None:
                        continue
                    self._ingestion_state_manager.increment_phase_progress(source_id, IngestionPhase.EMBEDDING, count)

            # Write the processed batch to output queue
            self._transport.write(batch)

            logger.debug(f"Successfully processed {len(batch)} text inputs")

        except Exception as e:
            logger.error(f"Failed to process batch of {len(batch)} inputs: {e}", exc_info=True)
            raise

    def process_batch(self, batch: TextBatch) -> TextBatch:
        """Process a single batch directly without using transport queues.

        This method provides a direct interface for processing batches without
        the queue-based transport layer. Useful for synchronous processing
        or testing scenarios.

        Args:
            batch: TextBatch containing inputs to vectorize

        Returns:
            The same TextBatch with vector embeddings set on each input

        Raises:
            TypeError: If batch is not a TextBatch instance
            Exception: May raise exceptions from the vectorizer
        """
        if not isinstance(batch, TextBatch):
            raise TypeError(f"Expected TextBatch, got {type(batch)}")

        if len(batch) == 0:
            logger.debug("Received empty batch, returning as-is")
            return batch

        logger.debug(f"Processing batch of {len(batch)} text inputs directly")

        try:
            self._vectorizer.vectorize(batch)
            logger.debug(f"Successfully processed {len(batch)} text inputs directly")
            return batch

        except Exception as e:
            logger.error(
                f"Failed to process batch of {len(batch)} inputs directly: {e}",
                exc_info=True,
            )
            raise


def get_embedder(
    transport: BulkQueueReadWriter,
    vectorizer: Optional[Vectorizer] = None,
    ingestion_state_manager: Optional[SourceIngestionProgressManager] = None,
) -> Embedder:
    """Factory function to create a configured Embedder instance.

    This factory provides a convenient way to create embedders with sensible
    defaults. If no vectorizer is provided, it creates a SentenceTransformerVectorizer
    using the configured model path.

    Args:
        transport: Transport layer for reading/writing batches
        vectorizer: Optional pre-configured vectorizer. If None, creates
                   a SentenceTransformerVectorizer with the configured model path.

    Returns:
        Configured Embedder instance ready for processing

    Raises:
        ValueError: If no model path is configured and no vectorizer provided
        TypeError: If transport is not a BulkQueueReadWriter
    """

    if vectorizer is None:
        logger.info(f"Creating SentenceTransformerVectorizer with model: {VECTORIZER_MODEL_PATH.value}")
        vectorizer = SentenceTransformerVectorizer(VECTORIZER_MODEL_PATH.value)

    return Embedder(transport, vectorizer, ingestion_state_manager)
