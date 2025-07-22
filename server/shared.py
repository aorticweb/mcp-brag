from dataclasses import dataclass
from typing import Generic, List, Optional, Set, TypeVar

from common.log import get_logger
from common.singleton import Singleton
from embedder.read_write.bulk_queue import BulkQueue
from embedder.store.store import DataSourceMap
from embedder.text import TextInput
from server.error import MCPError
from server.thread_managers.download_manager import DownloadManager
from server.thread_managers.embedder_manager import EmbedderThreadManager
from server.thread_managers.transcription_manager import (
    TranscriptionTask,
    TranscriptionThreadManager,
)
from server.workers.ingestion_state_manager import SourceIngestionProgressManager

logger = get_logger(__name__)


T = TypeVar("T")


class GlobalDependency(Generic[T]):
    """A wrapper class to hold global dependencies as singletons."""

    def __init__(self) -> None:
        """
        Initialize global dependency wrapper
        """
        self._instance: Optional[T] = None

    def set(self, instance: T) -> None:
        """
        Set the global instance

        Args:
            instance: The instance to set as global
        """
        self._instance = instance

    def get(self) -> T:
        """Get the global instance."""
        if self._instance is None:
            raise MCPError("Global dependency not initialized")
        return self._instance

    def is_initialized(self) -> bool:
        """Check if the instance is initialized."""
        return self._instance is not None


# Global dependency holders
global_embedder_read_queue = GlobalDependency[BulkQueue]()
global_embedder_write_queue = GlobalDependency[BulkQueue]()
global_embedder_manager = GlobalDependency[EmbedderThreadManager]()
global_data_source_map = GlobalDependency[DataSourceMap]()
global_download_bulk_queue = GlobalDependency[BulkQueue]()
global_download_manager = GlobalDependency[DownloadManager]()
global_transcription_queue = GlobalDependency[BulkQueue[TranscriptionTask]]()
global_transcription_manager = GlobalDependency[TranscriptionThreadManager]()
global_ingestion_state_manager = GlobalDependency[SourceIngestionProgressManager]()


@dataclass
class ActiveDataSources(metaclass=Singleton):
    active_data_sources: Optional[Set[str]] = None

    def __post_init__(self):
        """
        Initialize thread lock after dataclass initialization
        """
        import threading

        self._lock = threading.RLock()

    def __enter__(self):
        """
        Enter context manager and acquire lock

        Returns:
            ActiveDataSources: Self instance with acquired lock
        """
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context manager and release lock

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        self._lock.release()

    def validate_data_sources(self, data_sources: List[str]) -> List[str]:
        """
        Validate data sources against available sources

        Args:
            data_sources: List of data source identifiers to validate

        Returns:
            List[str]: List of valid data sources
        """
        available_sources = global_data_source_map.get().list_sources()
        unknown_data_sources = set(data_sources) - set(available_sources)
        if unknown_data_sources:
            logger.warning(f"Unknown data sources: {unknown_data_sources}")
        return list(set(data_sources) - unknown_data_sources)


def check_dependencies():
    """Check if dependencies are initialized.

    Raises:
        MCPError: If dependencies are not initialized
    """
    if (
        not global_embedder_read_queue.is_initialized()
        or not global_embedder_write_queue.is_initialized()
        or not global_embedder_manager.is_initialized()
        or not global_data_source_map.is_initialized()
        or not global_download_bulk_queue.is_initialized()
        or not global_download_manager.is_initialized()
        or not global_transcription_queue.is_initialized()
        or not global_transcription_manager.is_initialized()
        or not global_ingestion_state_manager.is_initialized()
    ):
        raise MCPError("Dependencies not initialized. Call initialize_dependencies() first.")


def get_embedder_read_queue() -> BulkQueue[TextInput]:
    """
    Get the global embedder read queue

    Returns:
        BulkQueue[TextInput]: Queue for reading text inputs to embed
    """
    return global_embedder_read_queue.get()


def get_embedder_manager() -> EmbedderThreadManager:
    """Get the embedder thread manager."""
    return global_embedder_manager.get()


def get_data_source_map() -> DataSourceMap:
    """
    Get the global data source map

    Returns:
        DataSourceMap: Map of available data sources
    """
    return global_data_source_map.get()


def get_download_bulk_queue() -> BulkQueue[str]:
    """Get the YouTube bulk download queue."""
    return global_download_bulk_queue.get()


def get_download_manager() -> DownloadManager:
    """Get the YouTube download manager."""
    return global_download_manager.get()


def get_transcription_queue() -> BulkQueue[TranscriptionTask]:
    """Get the transcription queue."""
    return global_transcription_queue.get()


def get_transcription_manager() -> TranscriptionThreadManager:
    """Get the transcription thread manager."""
    return global_transcription_manager.get()


def get_ingestion_state_manager() -> SourceIngestionProgressManager:
    """Get the ingestion state manager."""
    return global_ingestion_state_manager.get()
