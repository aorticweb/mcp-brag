from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from embedder.store.sqlite.sql import SqliteEmbeddingRow
from embedder.store.sqlite.sqlite import SqliteDataSourceMap, SqliteEmbeddingStore
from embedder.store.store import (
    CollectionState,
    DataSourceStats,
    RelevantCollection,
    TextInput,
    TextInputWithDistance,
)


class TestSqliteEmbeddingStore:
    """Test suite for SqliteEmbeddingStore class."""

    def test_init(self):
        """Test initialization of SqliteEmbeddingStore."""
        store = SqliteEmbeddingStore("test-collection")
        assert store._name == "test-collection"

    def test_name(self):
        """Test name property."""
        store = SqliteEmbeddingStore("test-collection")
        assert store.name() == "test-collection"

    @patch("embedder.store.sqlite.sqlite.insert_embeddings")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_add_batch(self, mock_conn_instance, mock_insert_embeddings):
        """Test adding a batch of text inputs."""
        # Setup mocks
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn

        store = SqliteEmbeddingStore("test-collection")

        # Create test data
        text_inputs = [
            TextInput(text="text1", metadata={"key1": "value1"}),
            TextInput(text="text2", metadata={"key2": "value2"}),
            TextInput(text="text3", metadata={}),
        ]

        # Set vectors (normally done by embedder)
        for i, ti in enumerate(text_inputs):
            ti._vec = np.array([i * 0.1, i * 0.2, i * 0.3], dtype=np.float32)

        # Call add_batch
        result_ids = store.add_batch(text_inputs)

        # Verify
        assert len(result_ids) == 3
        mock_insert_embeddings.assert_called_once()

        # Check the embeddings passed to insert
        call_args = mock_insert_embeddings.call_args[0]
        embeddings = call_args[1]
        assert len(embeddings) == 3
        assert all(isinstance(e, SqliteEmbeddingRow) for e in embeddings)
        assert embeddings[0].text == "text1"
        assert embeddings[1].text == "text2"
        assert embeddings[2].text == "text3"

    @patch("embedder.store.sqlite.sqlite.insert_embeddings")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_add_batch_with_custom_ids(self, mock_conn_instance, mock_insert_embeddings):
        """Test adding a batch with custom IDs in metadata."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn

        store = SqliteEmbeddingStore("test-collection")

        # Create test data with custom IDs
        custom_id = "custom-id-123"
        text_inputs = [TextInput(text="text1", metadata={"id": custom_id, "other": "data"})]
        text_inputs[0]._vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)

        result_ids = store.add_batch(text_inputs)

        # Verify custom ID was used
        assert result_ids[0] == custom_id
        call_args = mock_insert_embeddings.call_args[0]
        embeddings = call_args[1]
        assert embeddings[0].id == custom_id

    @patch("embedder.store.sqlite.sqlite.get_collections_details")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_vector_count(self, mock_conn_instance, mock_get_collections_details):
        """Test getting vector count."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn

        # Mock return value
        mock_stats = DataSourceStats(
            source_name="test",
            source_path="test-collection",
            status=CollectionState.COMPLETED,
            vector_count=42,
            dimension=768,
        )
        mock_get_collections_details.return_value = [mock_stats]

        store = SqliteEmbeddingStore("test-collection")
        count = store.vector_count()

        assert count == 42
        mock_get_collections_details.assert_called_once_with(mock_conn, ["test-collection"])

    @patch("embedder.store.sqlite.sqlite.get_collections_details")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_vector_count_no_collection(self, mock_conn_instance, mock_get_collections_details):
        """Test getting vector count when collection doesn't exist."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_collections_details.return_value = []

        store = SqliteEmbeddingStore("test-collection")
        count = store.vector_count()

        assert count == 0


class TestSqliteDataSourceMap:
    """Test suite for SqliteDataSourceMap class."""

    @patch("embedder.store.sqlite.sqlite.get_collection_sources")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_exists(self, mock_conn_instance, mock_get_sources):
        """Test checking if a source exists."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_sources.return_value = ["source1", "source2", "source3"]

        ds_map = SqliteDataSourceMap()

        assert ds_map.exists("source2") is True
        assert ds_map.exists("source4") is False

    @patch("embedder.store.sqlite.sqlite.get_collection_sources")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_get_existing_source(self, mock_conn_instance, mock_get_sources):
        """Test getting an existing source."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_sources.return_value = ["test-source"]

        ds_map = SqliteDataSourceMap()
        store = ds_map.get("test-source")

        assert isinstance(store, SqliteEmbeddingStore)
        assert store.name() == "test-source"

    @patch("embedder.store.sqlite.sqlite.get_collection_sources")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_get_nonexistent_source(self, mock_conn_instance, mock_get_sources):
        """Test getting a non-existent source raises error."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_sources.return_value = []

        ds_map = SqliteDataSourceMap()

        with pytest.raises(ValueError) as exc_info:
            ds_map.get("nonexistent")
        assert "Source nonexistent does not exist" in str(exc_info.value)

    @patch("embedder.store.sqlite.sqlite.create_collection")
    @patch("embedder.store.sqlite.sqlite.get_collection_sources")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_create_new_source(self, mock_conn_instance, mock_get_sources, mock_create_collection):
        """Test creating a new source."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_sources.return_value = []  # Source doesn't exist

        ds_map = SqliteDataSourceMap()
        store = ds_map.create("new-source", "pdf", "My PDF", CollectionState.PROCESSING)

        assert isinstance(store, SqliteEmbeddingStore)
        assert store.name() == "new-source"
        mock_create_collection.assert_called_once_with(
            mock_conn, "new-source", "My PDF", "pdf", CollectionState.PROCESSING
        )

    @patch("embedder.store.sqlite.sqlite.get_collection_sources")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_create_existing_source(self, mock_conn_instance, mock_get_sources):
        """Test creating a source that already exists."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_sources.return_value = ["existing-source"]

        ds_map = SqliteDataSourceMap()
        store = ds_map.create("existing-source", "text", None, CollectionState.PROCESSING)

        # Should return store without creating
        assert isinstance(store, SqliteEmbeddingStore)
        assert store.name() == "existing-source"

    @patch("embedder.store.sqlite.sqlite.delete_collection")
    @patch("embedder.store.sqlite.sqlite.get_collection_sources")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_delete_existing_source(self, mock_conn_instance, mock_get_sources, mock_delete_collection):
        """Test deleting an existing source."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_sources.return_value = ["test-source"]

        ds_map = SqliteDataSourceMap()
        result = ds_map.delete("test-source")

        assert result is True
        mock_delete_collection.assert_called_once_with(mock_conn, "test-source")

    @patch("embedder.store.sqlite.sqlite.get_collection_sources")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_delete_nonexistent_source(self, mock_conn_instance, mock_get_sources):
        """Test deleting a non-existent source."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_sources.return_value = []

        ds_map = SqliteDataSourceMap()
        result = ds_map.delete("nonexistent")

        assert result is False

    @patch("embedder.store.sqlite.sqlite.delete_collection_by_name")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_delete_by_name(self, mock_conn_instance, mock_delete_by_name):
        """Test deleting sources by name."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_delete_by_name.return_value = True

        ds_map = SqliteDataSourceMap()
        result = ds_map.delete_by_name("SharedName")

        assert result is True
        mock_delete_by_name.assert_called_once_with(mock_conn, "SharedName")

    @patch("embedder.store.sqlite.sqlite.update_collection_state")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_set_state(self, mock_conn_instance, mock_update_state):
        """Test setting collection state."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn

        ds_map = SqliteDataSourceMap()
        ds_map.set_state("test-source", CollectionState.COMPLETED)

        mock_update_state.assert_called_once_with(mock_conn, "test-source", CollectionState.COMPLETED)

    @patch("embedder.store.sqlite.sqlite.get_embedding_row_by_id")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_get_text_input_by_id(self, mock_conn_instance, mock_get_embedding):
        """Test getting text input by ID."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn

        # Mock embedding row
        mock_embedding_row = SqliteEmbeddingRow(
            id="test-id",
            collection="test-source",
            text="test text",
            embedding=np.array([0.1, 0.2, 0.3], dtype=np.float32),
            metadata={"key": "value"},
        )
        mock_get_embedding.return_value = mock_embedding_row

        ds_map = SqliteDataSourceMap()
        result = ds_map.get_text_input_by_id("test-id", "test-source")

        assert isinstance(result, TextInput)
        assert result._text == "test text"
        assert result._meta == {"key": "value"}
        np.testing.assert_array_almost_equal(result._vec, np.array([0.1, 0.2, 0.3], dtype=np.float32))

    @patch("embedder.store.sqlite.sqlite.get_embedding_row_by_id")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_get_text_input_by_id_not_found(self, mock_conn_instance, mock_get_embedding):
        """Test getting text input by ID when not found."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_embedding.return_value = None

        ds_map = SqliteDataSourceMap()
        result = ds_map.get_text_input_by_id("nonexistent", "test-source")

        assert result is None

    @patch("embedder.store.sqlite.sqlite.get_collection_sources")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_list_sources(self, mock_conn_instance, mock_get_sources):
        """Test listing all sources."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_sources.return_value = ["source1", "source2", "source3"]

        ds_map = SqliteDataSourceMap()
        sources = ds_map.list_sources()

        assert sources == ["source1", "source2", "source3"]

    @patch("embedder.store.sqlite.sqlite.get_collections_details")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_get_sources_stats(self, mock_conn_instance, mock_get_details):
        """Test getting statistics for all sources."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn

        mock_stats = [
            DataSourceStats("name1", "source1", CollectionState.COMPLETED, 100, 768),
            DataSourceStats("name2", "source2", CollectionState.PROCESSING, 50, 768),
        ]
        mock_get_details.return_value = mock_stats

        ds_map = SqliteDataSourceMap()
        stats = ds_map.get_sources_stats()

        assert len(stats) == 2
        assert "source1" in stats
        assert stats["source1"].vector_count == 100
        assert "source2" in stats
        assert stats["source2"].vector_count == 50

    @patch("embedder.store.sqlite.sqlite.get_collections_details")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_get_source_stats(self, mock_conn_instance, mock_get_details):
        """Test getting statistics for a specific source."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn

        mock_stats = [DataSourceStats("name1", "source1", CollectionState.COMPLETED, 100, 768)]
        mock_get_details.return_value = mock_stats

        ds_map = SqliteDataSourceMap()
        stats = ds_map.get_source_stats("source1")

        assert stats.source_path == "source1"
        assert stats.vector_count == 100

    @patch("embedder.store.sqlite.sqlite.get_collections_details")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_get_source_stats_not_found(self, mock_conn_instance, mock_get_details):
        """Test getting statistics for non-existent source."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_details.return_value = []

        ds_map = SqliteDataSourceMap()
        stats = ds_map.get_source_stats("nonexistent")

        assert stats.source_path == "nonexistent"
        assert stats.status == CollectionState.NOT_FOUND
        assert stats.vector_count == 0

    @patch("embedder.store.sqlite.sqlite.search_relevant_collections")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_get_relevant_sources(self, mock_conn_instance, mock_search_relevant):
        """Test getting relevant sources for a query."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn

        # Mock relevant collection
        mock_relevant = MagicMock()
        mock_relevant.to_relevant_collection.return_value = RelevantCollection(
            collection="test-collection", min_distance=0.1, avg_distance=0.5, count=10
        )
        mock_search_relevant.return_value = [mock_relevant]

        ds_map = SqliteDataSourceMap()
        query_vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        results = ds_map.get_relevant_sources(query_vec, limit=5, distance_threshold=2.0)

        assert len(results) == 1
        assert results[0].collection == "test-collection"
        mock_search_relevant.assert_called_once_with(mock_conn, query_vec, 5, None, 2.0)

    @patch("embedder.store.sqlite.sqlite.search_embeddings")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_search(self, mock_conn_instance, mock_search_embeddings):
        """Test searching for similar embeddings."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn

        # Mock search results
        mock_result = MagicMock()
        mock_result.text = "test text"
        mock_result.metadata = {"key": "value"}
        mock_result.embedding = np.array([0.1, 0.2], dtype=np.float32)
        mock_result.distance = 0.75
        mock_search_embeddings.return_value = [mock_result]

        ds_map = SqliteDataSourceMap()
        query_vec = np.array([0.15, 0.25], dtype=np.float32)
        results = ds_map.search(query_vec, sources=["source1"], k=10)

        assert len(results) == 1
        assert isinstance(results[0], TextInputWithDistance)
        assert results[0]._text == "test text"
        assert results[0]._distance == 0.75
        mock_search_embeddings.assert_called_once_with(mock_conn, query_vec, 10, ["source1"])

    def test_fail_ingestion_process_callback(self):
        """Test getting failure callback."""
        ds_map = SqliteDataSourceMap()
        ds_map.set_state = MagicMock()

        callback = ds_map.fail_ingestion_process_callback("test-source")
        callback()

        ds_map.set_state.assert_called_once_with("test-source", CollectionState.FAILED)

    def test_success_ingestion_process_callback(self):
        """Test getting success callback."""
        ds_map = SqliteDataSourceMap()
        ds_map.set_state = MagicMock()

        callback = ds_map.success_ingestion_process_callback("test-source")
        callback()

        ds_map.set_state.assert_called_once_with("test-source", CollectionState.COMPLETED)

    @patch("embedder.store.sqlite.sqlite.get_collection_sources")
    @patch("embedder.store.sqlite.sqlite.SqliteConnInstance")
    def test_dunder_methods(self, mock_conn_instance, mock_get_sources):
        """Test __len__, __contains__, and __iter__ methods."""
        mock_conn = MagicMock()
        mock_conn_instance.return_value.conn = mock_conn
        mock_get_sources.return_value = ["source1", "source2", "source3"]

        ds_map = SqliteDataSourceMap()

        # Test __len__
        assert len(ds_map) == 3

        # Test __contains__
        assert "source2" in ds_map
        assert "source4" not in ds_map

        # Test __iter__
        sources = list(ds_map)
        assert sources == ["source1", "source2", "source3"]
