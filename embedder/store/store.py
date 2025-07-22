import abc
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional

import numpy as np

from embedder.text import TextInput

USER_QUERY_SOURCE = "user-query"


class TextInputWithDistance:
    __slots__ = "_text", "_meta", "_vec", "_distance"
    _text: str
    _meta: Dict[str, Any]
    _vec: np.ndarray
    _distance: float

    def __init__(self, text: str, metadata: Dict[str, Any], vec: np.ndarray, distance: float):
        """
        Initialize text input with distance metric

        Args:
            text: Text content
            metadata: Associated metadata
            vec: Vector embedding
            distance: Distance metric from query
        """
        self._text = text
        self._meta = metadata
        self._vec = vec
        self._distance = distance

    @classmethod
    def from_text_input(cls, text_input: TextInput, distance: float) -> "TextInputWithDistance":
        """
        Create instance from TextInput with distance

        Args:
            text_input: Source TextInput object
            distance: Distance metric to add

        Returns:
            TextInputWithDistance: New instance with distance
        """
        return cls(text_input._text, text_input._meta, text_input._vec, distance)  # type: ignore

    def __str__(self) -> str:
        """
        String representation of the text input

        Returns:
            str: The text content
        """
        return self._text


class VectorStoreError(Exception):
    """Base exception for vector store operations."""

    pass


class CollectionState(str, Enum):
    NOT_FOUND = "not_found"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RelevantCollection:
    collection: str
    min_distance: float
    avg_distance: float
    count: int

    def to_dict(self) -> Dict:
        return {
            "collection": self.collection,
            "min_distance": self.min_distance,
            "avg_distance": self.avg_distance,
            "count": self.count,
        }


@dataclass
class DataSourceStats:
    source_name: str
    source_path: str
    status: CollectionState
    vector_count: int
    dimension: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EmbeddingStore(abc.ABC):
    @abc.abstractmethod
    def name(self) -> str:
        """
        Get the name of the store

        Returns:
            str: Store name
        """
        pass

    @abc.abstractmethod
    def add_batch(self, text_inputs: List[TextInput]) -> List[str]:
        """
        Add multiple TextInputs to the store efficiently.

        Args:
            text_inputs: List of TextInputs to add

        Returns:
            List of IDs assigned to the TextInputs
        """
        pass

    @abc.abstractmethod
    def vector_count(self) -> int:
        """
        Get the number of vectors in the store

        Returns:
            int: Number of vectors
        """
        pass


class DataSourceMap(abc.ABC):
    @abc.abstractmethod
    def create(
        self,
        source: str,
        source_type: str,
        source_name: Optional[str] = None,
        status: CollectionState = CollectionState.PROCESSING,
    ) -> EmbeddingStore:
        """
        Create the EmbeddingStore for source

        Args:
            source: Source location identifier for the EmbeddingStore
            source_type: Type of the source
            source_name: Optional name for the source
            status: Initial collection state (default: PROCESSING)

        Returns:
            EmbeddingStore: Instance for the specified source
        """
        pass

    @abc.abstractmethod
    def delete(self, source: str) -> bool:
        """Delete the EmbeddingStore for source.

        Args:
            source: Source location identifier for the EmbeddingStore

        Returns:
            True if the EmbeddingStore was deleted, False if it was not found
        """
        pass

    @abc.abstractmethod
    def delete_by_name(self, source_name: str) -> bool:
        """Delete the EmbeddingStore(s) for source_name.

        Args:
            source_name: Source name

        Returns:
            True if at least one EmbeddingStore was deleted, False if none were found
        """
        pass

    @abc.abstractmethod
    def exists(self, source: str) -> bool:
        """
        Check if the EmbeddingStore for source exists

        Args:
            source: Source location identifier for the EmbeddingStore

        Returns:
            bool: True if store exists, False otherwise
        """
        pass

    @abc.abstractmethod
    def get(self, source: str) -> EmbeddingStore:
        """Get the EmbeddingStore for source.

        Args:
            source: Source location identifier for the EmbeddingStore

        Returns:
            Existing EmbeddingStore for the source, or an empty store with no index
        """
        pass

    @abc.abstractmethod
    def get_text_input_by_id(self, id: str, source: str) -> Optional[TextInput]:
        """Get the TextInput for the specified ID from the specified source.

        Args:
            id: ID of the TextInput to retrieve
            source: Source location of the TextInput

        Returns:
            TextInput if found, None if the source doesn't exist or ID is not found
        """
        pass

    @abc.abstractmethod
    def list_sources(self) -> List[str]:
        """Get a list of all registered data sources.

        Returns:
            List of source identifiers
        """
        pass

    @abc.abstractmethod
    def get_sources_stats(self) -> Dict[str, DataSourceStats]:
        """Get statistics for all sources.

        Returns:
            Dictionary mapping source to its statistics
        """
        pass

    @abc.abstractmethod
    def get_source_stats(self, source: str) -> DataSourceStats:
        """
        Get statistics for a specific source

        Args:
            source: Source identifier

        Returns:
            DataSourceStats: Statistics for the specified source
        """
        pass

    @abc.abstractmethod
    def get_source_stats_by_name(self, source_name: str) -> List[DataSourceStats]:
        """
        Get statistics for specific sources, filtered by name

        Args:
            source_name: Name to filter sources by

        Returns:
            List[DataSourceStats]: Statistics for the matching sources
        """
        pass

    @abc.abstractmethod
    def get_sources(self) -> List[EmbeddingStore]:
        """Get a list of all registered data sources.

        Returns:
            List of source identifiers
        """
        pass

    @abc.abstractmethod
    def get_relevant_sources(
        self, query_vec: np.ndarray, limit: int, distance_threshold: float = 10.0, sources: Optional[List[str]] = None
    ) -> List[RelevantCollection]:
        """
        Get a list of the most relevant data sources for a query

        Args:
            query_vec: Query vector to search for
            limit: Maximum number of sources to return
            distance_threshold: Maximum distance threshold for relevance
            sources: Optional list of sources to search within

        Returns:
            List[RelevantCollection]: Most relevant sources with statistics
        """
        pass

    @abc.abstractmethod
    def search(
        self, query_vec: np.ndarray, sources: Optional[List[str]] = None, k: int = 20
    ) -> List[TextInputWithDistance]:
        """Search for k nearest neighbors of query vector.

        Args:
            query_vec: Query vector to search for
            sources: List of sources to search in (optional)
            k: Number of nearest neighbors to return (must be positive)

        Returns:
            List of up to k most similar TextInputs, ordered by similarity (most similar first)

        Raises:
            ValueError: If k is not positive or query_vec is invalid
        """
        pass

    @abc.abstractmethod
    def set_state(self, source: str, state: CollectionState):
        """
        Set the state of the collection

        Args:
            source: Source identifier
            state: New state for the collection
        """
        pass

    @abc.abstractmethod
    def fail_ingestion_process_callback(self, source: str) -> Callable[[], None]:
        """
        Get the callback to call when the ingestion process fails

        Args:
            source: Source identifier

        Returns:
            Callable[[], None]: Callback function for failure
        """
        pass

    @abc.abstractmethod
    def success_ingestion_process_callback(self, source: str) -> Callable[[], None]:
        """
        Get the callback to call when the ingestion process succeeds

        Args:
            source: Source identifier

        Returns:
            Callable[[], None]: Callback function for success
        """
        pass

    @abc.abstractmethod
    def __len__(self) -> int:
        """
        Return the number of data sources

        Returns:
            int: Number of data sources
        """
        pass

    @abc.abstractmethod
    def __contains__(self, source: str) -> bool:
        """
        Check if a data source exists

        Args:
            source: Source identifier to check

        Returns:
            bool: True if source exists, False otherwise
        """
        pass

    @abc.abstractmethod
    def __iter__(self) -> Iterator[str]:
        """
        Iterate over source names

        Returns:
            Iterator[str]: Iterator over source identifiers
        """
        pass
