import abc
import threading
from datetime import datetime, timedelta
from typing import Optional

from common.log import get_logger

logger = get_logger(__name__)


class SelfTerminatingThreadManager(abc.ABC):
    def __init__(
        self,
        activity_timeout: Optional[timedelta] = None,
        thread_terimination_timeout: timedelta = timedelta(seconds=300),
    ):
        self._activity_timeout = activity_timeout
        self._should_stop = False
        self._last_activity = datetime.now()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._thread_terimination_timeout = thread_terimination_timeout

    @abc.abstractmethod
    def run(self):
        """Run the thread manager."""
        pass

    @abc.abstractmethod
    def name(self) -> str:
        """Return the name of the thread manager."""
        pass

    def ensure_running(self):
        """Ensure the consumer thread is running, start it if necessary."""
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                logger.info(f"{self.name()} thread not running, starting it")
                # Reset control variables
                self._should_stop = False
                self._last_activity = datetime.now()

                # Start new thread
                self._thread = threading.Thread(target=self.run, name=self.name())
                self._thread.start()
            else:
                # Thread is running, update activity time
                self._last_activity = datetime.now()

    def stop(self):
        """Stop the consumer thread gracefully."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                logger.info("Stopping YouTube download consumer thread")
                self._should_stop = True
                self._thread.join(
                    timeout=max(int(self._thread_terimination_timeout.total_seconds()), 10)
                )  # Wait up to 10 seconds
                if self._thread.is_alive():
                    logger.warning(f"{self.name()} thread did not stop gracefully")

    def is_running(self) -> bool:
        """Check if the consumer thread is currently running."""
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def should_terminate_due_to_idle(self) -> bool:
        """Check if the thread should terminate due to idle timeout."""
        if self._activity_timeout is None:
            return False
        idle_time = datetime.now() - self._last_activity
        is_expired = idle_time.total_seconds() > self._activity_timeout.total_seconds()
        if is_expired:
            logger.info(f"{self.name()} thread has been idle for {idle_time.total_seconds()} seconds")
        return is_expired

    def mark_as_active(self):
        """Mark the thread as active."""
        self._last_activity = datetime.now()
