from typing import Callable, Dict, Iterator, List, Optional, Union
from uuid import uuid4

import numpy as np

from common.log import get_logger
from embedder.store.sqlite.sql import (
    SqliteConnInstance,
    SqliteEmbeddingRow,
    create_collection,
    delete_collection,
    delete_collection_by_name,
    delete_embeddings,
    get_collection_sources,
    get_collections_details,
    get_collections_details_by_name,
    get_embedding_row_by_id,
    insert_embeddings,
    search_embeddings,
    search_relevant_collections,
    update_collection_state,
)
from embedder.store.store import (
    CollectionState,
    DataSourceMap,
    DataSourceStats,
    EmbeddingStore,
    RelevantCollection,
    TextInput,
    TextInputWithDistance,
)

logger = get_logger(__name__)


class SqliteEmbeddingStore(EmbeddingStore):
    _name: str

    def __init__(self, name: str):
        self._name = name

    def name(self) -> str:
        """Get the name of the store."""
        return self._name

    def add_batch(self, text_inputs: List[TextInput]) -> List[str]:
        """
        Add multiple TextInputs to the store efficiently.

        Args:
            text_inputs: List of TextInputs to add

        Returns:
            List of IDs assigned to the TextInputs
        """
        embedding_rows: List[SqliteEmbeddingRow] = []
        for text_input in text_inputs:
            embedding_rows.append(
                SqliteEmbeddingRow(
                    id=text_input._meta.get("id", str(uuid4())),
                    collection=self._name,
                    text=text_input._text,
                    embedding=text_input._vec,  # type: ignore
                    metadata=text_input._meta,
                )
            )
        insert_embeddings(SqliteConnInstance().conn, embedding_rows)
        logger.debug(f"Added {len(embedding_rows)} embeddings to {self._name}")
        return [embedding_row.id for embedding_row in embedding_rows]

    def vector_count(self) -> int:
        """Get the number of vectors in the store."""
        conn = SqliteConnInstance().conn
        stats = get_collections_details(conn, [self._name])
        if len(stats) == 0:
            return 0
        return stats[0].vector_count


class SqliteDataSourceMap(DataSourceMap):
    def exists(self, source: str) -> bool:
        """Check if the EmbeddingStore for source exists.

        Args:
            source: Source location identifier for the EmbeddingStore
        """
        conn = SqliteConnInstance().conn
        return source in get_collection_sources(conn)

    def get(self, source: str) -> EmbeddingStore:
        """Get the EmbeddingStore for source.

        Args:
            source: Source location identifier for the EmbeddingStore

        Returns:
            EmbeddingStore instance for the specified source
        """
        conn = SqliteConnInstance().conn
        if source not in get_collection_sources(conn):
            raise ValueError(f"Source {source} does not exist")
        return SqliteEmbeddingStore(source)

    def create(
        self,
        source: str,
        source_type: str,
        source_name: Optional[str] = None,
        status: CollectionState = CollectionState.PROCESSING,
    ) -> EmbeddingStore:
        """Create the EmbeddingStore for source.

        Args:
            source: Source location identifier for the EmbeddingStore

        Returns:
            EmbeddingStore instance for the specified source
        """
        conn = SqliteConnInstance().conn
        if source not in get_collection_sources(conn):
            create_collection(conn, source, source_name, source_type, status)
        return SqliteEmbeddingStore(source)

    def delete(self, source: str) -> bool:
        """Delete the EmbeddingStore for source.

        Args:
            source: Source location identifier for the EmbeddingStore
        """
        conn = SqliteConnInstance().conn
        if source not in get_collection_sources(conn):
            return False
        delete_collection(conn, source)
        return True

    def delete_by_name(self, source_name: str) -> bool:
        """Delete the EmbeddingStore(s) for source_name.

        Args:
            source_name: Source name

        Returns:
            True if at least one EmbeddingStore was deleted, False if none were found
        """
        conn = SqliteConnInstance().conn
        return delete_collection_by_name(conn, source_name)

    def set_state(self, source: str, state: CollectionState):
        """Set the state of the collection."""
        conn = SqliteConnInstance().conn
        update_collection_state(conn, source, state)

    def get_text_input_by_id(self, id: Union[str, int], source: str) -> Optional[TextInput]:
        """Get the TextInput for the specified ID from the specified source.

        Args:
            id: ID of the TextInput to retrieve
            source: Source location of the TextInput

        Returns:
            TextInput if found, None if the source doesn't exist or ID is not found
        """
        conn = SqliteConnInstance().conn
        embedding_row = get_embedding_row_by_id(conn, str(id), source)
        if embedding_row is None:
            return None

        text_input = TextInput(text=embedding_row.text, metadata=embedding_row.metadata or {})
        text_input._vec = embedding_row.embedding
        return text_input

    def list_sources(self) -> List[str]:
        """Get a list of all registered data sources.

        Returns:
            List of source identifiers
        """
        conn = SqliteConnInstance().conn
        return get_collection_sources(conn)

    def get_sources_stats(self) -> Dict[str, DataSourceStats]:
        """Get statistics for all sources.

        Returns:
            Dictionary mapping source to its statistics
        """
        conn = SqliteConnInstance().conn
        return {collection.source_path: collection for collection in get_collections_details(conn)}

    def get_source_stats(self, source: str) -> DataSourceStats:
        """Get statistics for a specific source.

        Returns:
            Statistics for the specified source
        """
        conn = SqliteConnInstance().conn
        collections = get_collections_details(conn, [source])
        if len(collections) == 0:
            return DataSourceStats(
                source_name=source,
                source_path=source,
                status=CollectionState.NOT_FOUND,
                vector_count=0,
                dimension=0,
            )
        return collections[0]

    def get_source_stats_by_name(self, source_name: str) -> List[DataSourceStats]:
        """Get statistics for specific sources, filtered by name.

        Returns:
            Statistics for the specified sources
        """
        conn = SqliteConnInstance().conn
        collections = get_collections_details_by_name(conn, source_name)
        return collections

    def get_sources(self) -> List[EmbeddingStore]:
        """Get a list of all registered data sources.

        Returns:
            List of source identifiers
        """
        conn = SqliteConnInstance().conn
        embedding_stores: List[EmbeddingStore] = []
        for collection in get_collection_sources(conn):
            embedding_stores.append(SqliteEmbeddingStore(collection))
        return embedding_stores

    def get_relevant_sources(
        self, query_vec: np.ndarray, limit: int, distance_threshold: float = 2.0, sources: Optional[List[str]] = None
    ) -> List[RelevantCollection]:
        """Get a list of the most relevant data sources for a query."""
        conn = SqliteConnInstance().conn
        relevant_collections = search_relevant_collections(conn, query_vec, limit, sources, distance_threshold)
        return [relevant_collection.to_relevant_collection() for relevant_collection in relevant_collections]

    def search(
        self, query_vec: np.ndarray, sources: Optional[List[str]] = None, k: int = 20
    ) -> List[TextInputWithDistance]:
        """Search for k nearest neighbors of query vector.

        Args:
            query_vec: Query vector to search for
            sources: List of sources to search in (optional)
            k: Number of nearest neighbors to return (must be positive)

        Returns:
            List of k most similar TextInputs, ordered by similarity (most similar first)

        Raises:
            ValueError: If k is not positive or query_vec is invalid
        """
        conn = SqliteConnInstance().conn
        embedding_rows = search_embeddings(conn, query_vec, k, sources)
        results = []
        for embedding_row in embedding_rows:
            results.append(
                TextInputWithDistance(
                    text=embedding_row.text,
                    metadata=embedding_row.metadata or {},
                    vec=embedding_row.embedding,
                    distance=embedding_row.distance,
                )
            )
        logger.debug(f"SQlite data source class: Search embeddings found {len(results)} results")
        return results

    def fail_ingestion_process_callback(self, source: str) -> Callable[[], None]:
        """Get the callback to call when the ingestion process fails."""

        def callback():
            self.set_state(source, CollectionState.FAILED)

        return callback

    def success_ingestion_process_callback(self, source: str) -> Callable[[], None]:
        """Get the callback to call when the ingestion process succeeds."""

        def callback():
            self.set_state(source, CollectionState.COMPLETED)

        return callback

    def __len__(self) -> int:
        """Return the number of data sources."""
        return len(list(self.__iter__()))

    def __contains__(self, source: str) -> bool:
        """Check if a data source exists."""
        return source in self.__iter__()

    def __iter__(self) -> Iterator[str]:
        """Iterate over source names."""
        conn = SqliteConnInstance().conn
        for collection in get_collection_sources(conn):
            yield collection

    def delete_vectors(self, source: Optional[str] = None) -> int:
        """Delete all vectors for a specific data source or all sources if source is None.

        Args:
            source: Source identifier whose vectors should be deleted
        """
        conn = SqliteConnInstance().conn
        return delete_embeddings(conn, source)
