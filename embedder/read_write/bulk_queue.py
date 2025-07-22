import time
from dataclasses import dataclass
from datetime import timedelta
from queue import Empty, Full, Queue
from threading import Lock
from typing import Callable, Generic, List, Optional, TypeVar

from common.config.field import int_env_field, timedelta_env_field
from common.log import get_logger
from embedder.constants import BULK_QUEUE_FULL_RETRY_COUNT, BULK_QUEUE_FULL_SLEEP_TIME
from embedder.text import TextBatch, TextInput

logger = get_logger(__name__)


T = TypeVar("T")


class BulkQueue(Generic[T]):
    """A thread-safe queue implementation optimized for efficient bulk read/write operations.

    This queue wraps the standard Queue class and provides atomic bulk operations
    to reduce lock contention and improve performance for batch processing scenarios.

    The queue supports:
    - Thread-safe single item operations (put_nowait, get_nowait)
    - Atomic bulk operations (put_many, get_many)
    - Standard queue operations (task_done, qsize)

    Attributes:
        _queue: The underlying Queue instance
        _lock: Thread lock for ensuring atomic bulk operations
    """

    def __init__(self, maxsize: int = 100, wake_consumer_function: Optional[Callable[[], None]] = None) -> None:
        """Initialize the bulk queue.

        Args:
            maxsize: Maximum queue size. 0 means unlimited size.
        """
        self._queue: Queue[T] = Queue(maxsize=maxsize)
        self._lock = Lock()
        self._wake_consumer_function = wake_consumer_function

    def put_nowait(self, item: T) -> None:
        """Put an item into the queue without waiting.

        Args:
            item: Item to put in the queue

        Raises:
            queue.Full: If queue is full and cannot accept the item
        """
        self.wake_consumer()
        self._queue.put_nowait(item)

    def set_wake_consumer_function(self, wake_consumer_function: Callable[[], None]) -> None:
        """
        Set the wake consumer function

        Args:
            wake_consumer_function: Function to call when waking up consumer
        """
        self._wake_consumer_function = wake_consumer_function

    def wake_consumer(self) -> None:
        """
        Wake up the consumer thread when queue is not empty
        """
        if self._wake_consumer_function:
            self._wake_consumer_function()

    def get_nowait(self) -> T:
        """Get an item from the queue without waiting.

        Returns:
            The next item from the queue

        Raises:
            queue.Empty: If queue is empty
        """
        return self._queue.get_nowait()

    def put_many(self, items: List[T], _retry_count: int = 0) -> None:
        """Put multiple items into the queue atomically with retry logic.

        This method attempts to put all items into the queue atomically. If the queue
        becomes full during the operation, it will retry with exponential backoff.

        Args:
            items: List of items to put in the queue
            _retry_count: Internal parameter for tracking retry attempts

        Raises:
            queue.Full: If queue doesn't have space for all items after all retries
        """
        if not items:  # Early return for empty list
            return

        with self._lock:
            remaining_items = list(items)  # Create a copy to avoid modifying original
            self.wake_consumer()

            for i, item in enumerate(remaining_items):
                try:
                    self._queue.put_nowait(item)
                except Full:
                    # Remove successfully added items and retry with remaining
                    remaining_items = remaining_items[i:]

                    if _retry_count < BULK_QUEUE_FULL_RETRY_COUNT.value:
                        # Exponential backoff with jitter
                        sleep_time = min(BULK_QUEUE_FULL_SLEEP_TIME.value * (2**_retry_count), 1.0)
                        time.sleep(sleep_time)
                        # Recursive call with remaining items only
                        self.put_many(remaining_items, _retry_count + 1)
                        return
                    else:
                        raise Full("Queue remained full after maximum retry attempts")

    def get_many(self, max_items: int) -> List[T]:
        """Get multiple items from the queue atomically.

        Args:
            max_items: Maximum number of items to retrieve. Must be positive.

        Returns:
            List of items retrieved from the queue. May be shorter than max_items
            if the queue doesn't contain enough items.

        Raises:
            ValueError: If max_items is not positive
        """
        if max_items <= 0:
            raise ValueError("max_items must be positive")

        items = []
        with self._lock:
            for _ in range(max_items):
                try:
                    items.append(self._queue.get_nowait())
                except Empty:
                    break
        return items

    def get_one(self) -> Optional[T]:
        """
        Get one item from the queue without waiting

        Returns:
            Optional[T]: The next item from the queue or None if empty
        """
        values = self.get_many(1)
        if values:
            return values[0]
        return None

    def task_done(self) -> None:
        """Mark a task as done.

        This should be called once for each item retrieved from the queue
        to indicate that processing is complete.
        """
        self._queue.task_done()

    def qsize(self) -> int:
        """Return the approximate size of the queue.

        Returns:
            The approximate number of items in the queue. Note that this
            size may change between the time this method returns and
            when the value is used.
        """
        return self._queue.qsize()

    def empty(self) -> bool:
        """Return True if the queue is empty, False otherwise.

        Returns:
            True if queue appears empty, False otherwise. This is only
            a snapshot and may change immediately after the call.
        """
        return self._queue.empty()

    def full(self) -> bool:
        """Return True if the queue is full, False otherwise.

        Returns:
            True if queue appears full, False otherwise. This is only
            a snapshot and may change immediately after the call.
        """
        return self._queue.full()


@dataclass
class BulkQueueConfig:
    """Configuration class for BulkQueueReadWriter behavior.

    This class defines configurable parameters for queue operations including
    batch sizes, sleep intervals, and queue size limits. All values can be
    overridden via environment variables.

    Attributes:
        batch_size: Number of items to process in each batch operation
        sleep: Time to sleep when no items are available for reading
        max_queue_size: Maximum number of items allowed in each queue
    """

    batch_size: int = int_env_field("ASYNC_QUEUE_BATCH_SIZE", 100)
    sleep: timedelta = timedelta_env_field("ASYNC_QUEUE_READ_SLEEP", timedelta(milliseconds=50))
    max_queue_size: int = int_env_field("ASYNC_QUEUE_MAX_SIZE", 100000)


class BulkQueueReadWriter:
    """A read/write interface for bulk queue operations with batch processing.

    This class provides a higher-level interface for reading and writing text batches
    to/from bulk queues. It handles batching logic and sleep behavior automatically.

    The reader will attempt to read up to batch_size items at once and will sleep
    when no items are available. The writer accepts TextBatch objects and puts
    all items atomically.

    Attributes:
        _read_queue: Queue for reading text inputs
        _write_queue: Queue for writing text outputs
        _batch_size: Maximum number of items to read in one operation
        _sleep_time: Time to sleep when read queue is empty
    """

    def __init__(
        self,
        read_queue: Optional[BulkQueue[TextInput]] = None,
        write_queue: Optional[BulkQueue[TextInput]] = None,
    ) -> None:
        """Initialize the read/write interface.

        Args:
            read_queue: Optional existing queue for reading. If None, creates new queue.
            write_queue: Optional existing queue for writing. If None, creates new queue.
        """
        cfg = BulkQueueConfig()
        self._read_queue = read_queue or BulkQueue(maxsize=cfg.max_queue_size)
        self._write_queue = write_queue or BulkQueue(maxsize=cfg.max_queue_size)
        self._batch_size = cfg.batch_size
        self._sleep_time = cfg.sleep

        logger.debug(
            "BulkQueueReadWriter initialized with "
            f"batch_size={cfg.batch_size}, "
            f"max_queue_size={cfg.max_queue_size}, "
            f"sleep_time={cfg.sleep.total_seconds(): .3f}s"
        )

    def read(self) -> TextBatch:
        """Read a batch of text inputs from the read queue.

        Attempts to read up to batch_size items from the queue. If no items
        are available and sleep_time is configured, will sleep to avoid
        busy waiting.

        Returns:
            TextBatch containing the retrieved items. May be empty if no
            items were available.
        """
        # Try to read multiple items at once for better performance
        items = self._read_queue.get_many(self._batch_size)

        # Mark each retrieved item as done for proper queue lifecycle management
        for _ in items:
            self._read_queue.task_done()

        # Sleep only if no items were retrieved and sleep is configured
        if not items and self._sleep_time > timedelta():
            time.sleep(self._sleep_time.total_seconds())

        return TextBatch(items)

    def write(self, batch: TextBatch) -> None:
        """Write a text batch to the write queue atomically.

        Args:
            batch: TextBatch containing inputs to write to the queue

        Raises:
            queue.Full: If the queue cannot accept all items in the batch
        """
        if batch.inputs:  # Only attempt write if there are items
            self._write_queue.put_many(batch.inputs)

    @property
    def read_queue_size(self) -> int:
        """Get the current size of the read queue.

        Returns:
            Number of items currently in the read queue
        """
        return self._read_queue.qsize()

    @property
    def write_queue_size(self) -> int:
        """Get the current size of the write queue.

        Returns:
            Number of items currently in the write queue
        """
        return self._write_queue.qsize()
