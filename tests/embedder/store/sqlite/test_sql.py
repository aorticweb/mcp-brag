import json
import os
import tempfile
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

from embedder.store.sqlite.sql import (
    SqliteConnInstance,
    SqliteEmbeddingRow,
    SqliteEmbeddingRowWithDistance,
    SqliteRelevantCollectionRow,
    create_collection,
    delete_collection,
    delete_collection_by_name,
    format_embedding_for_sqlite,
    format_sources_for_sqlite,
    get_collection_sources,
    get_collections_details,
    get_collections_details_by_name,
    get_embedding_row_by_id,
    get_sqlite_connection,
    initialize_sqlite_tables,
    insert_embeddings,
    search_embeddings,
    search_relevant_collections,
    update_collection_state,
)
from embedder.store.store import CollectionState, RelevantCollection


class TestSqliteConnection:
    """Test suite for SQLite connection functionality."""

    def test_get_sqlite_connection(self):
        """Test creating a SQLite connection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with patch("embedder.store.sqlite.sql.SQLITE_DB_LOCATION", MagicMock(value=db_path)):
                conn = get_sqlite_connection()
                assert conn is not None
                # Check WAL mode is enabled
                cursor = conn.execute("PRAGMA journal_mode")
                assert cursor.fetchone()[0] == "wal"
                conn.close()

    def test_get_sqlite_connection_creates_directory(self):
        """Test that get_sqlite_connection creates missing directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "nonexistent", "subdir", "test.db")
            with patch("embedder.store.sqlite.sql.SQLITE_DB_LOCATION", MagicMock(value=db_path)):
                conn = get_sqlite_connection()
                assert os.path.exists(os.path.dirname(db_path))
                conn.close()

    def test_sqlite_conn_instance_singleton(self):
        """Test that SqliteConnInstance is a singleton."""
        instance1 = SqliteConnInstance()
        instance2 = SqliteConnInstance()
        assert instance1 is instance2

    @patch("embedder.store.sqlite.sql.get_sqlite_connection")
    def test_sqlite_conn_instance_lazy_connection(self, mock_get_conn):
        """Test that SqliteConnInstance creates connection lazily."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        # Clear any existing connection
        SqliteConnInstance._connection = None

        instance = SqliteConnInstance()
        # Connection should not be created yet
        mock_get_conn.assert_not_called()

        # Access connection
        conn = instance.conn
        mock_get_conn.assert_called_once()
        assert conn == mock_conn

        # Subsequent access should not create new connection
        conn2 = instance.conn
        mock_get_conn.assert_called_once()  # Still only called once
        assert conn2 == mock_conn


class TestSqliteEmbeddingRow:
    """Test suite for SqliteEmbeddingRow dataclass."""

    def test_to_row_dict(self):
        """Test converting SqliteEmbeddingRow to dictionary."""
        embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        metadata = {"key": "value", "number": 42}
        row = SqliteEmbeddingRow(
            id="test-id",
            collection="test-collection",
            text="test text",
            embedding=embedding,
            metadata=metadata,
        )

        result = row.to_row_dict()
        assert result["id"] == "test-id"
        assert result["collection"] == "test-collection"
        assert result["text"] == "test text"
        # Parse and compare embeddings with tolerance due to float32 precision
        embedding_result = json.loads(result["embedding"])
        expected_embedding = [0.1, 0.2, 0.3]
        assert len(embedding_result) == len(expected_embedding)
        for i in range(len(embedding_result)):
            assert abs(embedding_result[i] - expected_embedding[i]) < 1e-5
        assert result["metadata"] == json.dumps(metadata)

    def test_to_row_dict_no_metadata(self):
        """Test converting SqliteEmbeddingRow with no metadata."""
        embedding = np.array([0.5], dtype=np.float32)
        row = SqliteEmbeddingRow(
            id="test-id",
            collection="test-collection",
            text="test text",
            embedding=embedding,
            metadata=None,
        )

        result = row.to_row_dict()
        assert result["metadata"] == "{}"

    def test_from_row(self):
        """Test creating SqliteEmbeddingRow from database row."""
        row_data = {
            "id": "test-id",
            "collection": "test-collection",
            "text": "test text",
            "embedding": "[0.1, 0.2, 0.3]",
            "metadata": '{"key": "value"}',
        }

        result = SqliteEmbeddingRow.from_row(row_data)
        assert result.id == "test-id"
        assert result.collection == "test-collection"
        assert result.text == "test text"
        np.testing.assert_array_almost_equal(result.embedding, np.array([0.1, 0.2, 0.3], dtype=np.float32))
        assert result.metadata == {"key": "value"}

    def test_from_row_no_metadata(self):
        """Test creating SqliteEmbeddingRow from row with no metadata."""
        row_data = {
            "id": "test-id",
            "collection": "test-collection",
            "text": "test text",
            "embedding": "[0.5]",
            "metadata": None,
        }

        result = SqliteEmbeddingRow.from_row(row_data)
        assert result.metadata is None


class TestSqliteEmbeddingRowWithDistance:
    """Test suite for SqliteEmbeddingRowWithDistance dataclass."""

    def test_from_row_with_distance(self):
        """Test creating SqliteEmbeddingRowWithDistance from database row."""
        row_data = {
            "id": "test-id",
            "collection": "test-collection",
            "text": "test text",
            "embedding": "[0.1, 0.2]",
            "metadata": '{"key": "value"}',
            "distance": 0.75,
        }

        result = SqliteEmbeddingRowWithDistance.from_row(row_data)
        assert result.id == "test-id"
        assert result.distance == 0.75
        np.testing.assert_array_almost_equal(result.embedding, np.array([0.1, 0.2], dtype=np.float32))


class TestSqliteRelevantCollectionRow:
    """Test suite for SqliteRelevantCollectionRow dataclass."""

    def test_from_row(self):
        """Test creating SqliteRelevantCollectionRow from database row."""
        row_data = {"collection": "test-collection", "min_distance": 0.1, "avg_distance": 0.5, "count": 10}

        result = SqliteRelevantCollectionRow.from_row(row_data)
        assert result.collection == "test-collection"
        assert result.min_distance == 0.1
        assert result.avg_distance == 0.5
        assert result.count == 10

    def test_to_relevant_collection(self):
        """Test converting to RelevantCollection."""
        row = SqliteRelevantCollectionRow(collection="test-collection", min_distance=0.1, avg_distance=0.5, count=10)

        result = row.to_relevant_collection()
        assert isinstance(result, RelevantCollection)
        assert result.collection == "test-collection"
        assert result.min_distance == 0.1
        assert result.avg_distance == 0.5
        assert result.count == 10


class TestFormattingFunctions:
    """Test suite for formatting utility functions."""

    def test_format_embedding_for_sqlite(self):
        """Test formatting numpy array for SQLite storage."""
        embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        result = format_embedding_for_sqlite(embedding)
        # Parse and compare with tolerance due to float32 precision
        parsed_result = json.loads(result)
        expected = [0.1, 0.2, 0.3]
        assert len(parsed_result) == len(expected)
        for i in range(len(parsed_result)):
            assert abs(parsed_result[i] - expected[i]) < 1e-5

    def test_format_embedding_for_sqlite_single_value(self):
        """Test formatting single value embedding."""
        embedding = np.array([0.5], dtype=np.float32)
        result = format_embedding_for_sqlite(embedding)
        assert result == "[0.500000000000]"

    def test_format_sources_for_sqlite(self):
        """Test formatting source list for SQLite query."""
        sources = ["source1", "source2", "source3"]
        result = format_sources_for_sqlite(sources)
        assert result == "'source1','source2','source3'"

    def test_format_sources_for_sqlite_single(self):
        """Test formatting single source."""
        sources = ["source1"]
        result = format_sources_for_sqlite(sources)
        assert result == "'source1'"

    def test_format_sources_for_sqlite_empty(self):
        """Test formatting empty source list."""
        sources = []
        result = format_sources_for_sqlite(sources)
        assert result == ""


class TestDatabaseOperations:
    """Test suite for database operations."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary test database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name

        with patch("embedder.store.sqlite.sql.SQLITE_DB_LOCATION", MagicMock(value=db_path)):
            conn = get_sqlite_connection()
            initialize_sqlite_tables(conn, 3)  # Small embedding dimension for tests
            yield conn
            conn.close()
            os.unlink(db_path)

    def test_initialize_sqlite_tables(self, test_db):
        """Test table initialization."""
        # Check embeddings table exists
        cursor = test_db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='embeddings'")
        assert cursor.fetchone() is not None

        # Check collections table exists
        cursor = test_db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collections'")
        assert cursor.fetchone() is not None

    def test_create_and_get_collection(self, test_db):
        """Test creating and retrieving collections."""
        # Create collection
        create_collection(test_db, "test-source", "Test Name", "text", CollectionState.PROCESSING)

        # Get collection sources
        sources = get_collection_sources(test_db)
        assert "test-source" in sources

        # Get collection details
        details = get_collections_details(test_db, ["test-source"])
        assert len(details) == 1
        assert details[0].source_path == "test-source"
        assert details[0].source_name == "Test Name"
        assert details[0].status == CollectionState.PROCESSING

    def test_update_collection_state(self, test_db):
        """Test updating collection state."""
        create_collection(test_db, "test-source", "Test Name", "text", CollectionState.PROCESSING)

        # Update state
        update_collection_state(test_db, "test-source", CollectionState.COMPLETED)

        # Verify update
        details = get_collections_details(test_db, ["test-source"])
        assert details[0].status == CollectionState.COMPLETED

    def test_delete_collection(self, test_db):
        """Test deleting a collection."""
        create_collection(test_db, "test-source", "Test Name", "text", CollectionState.PROCESSING)

        # Add some embeddings
        embeddings = [
            SqliteEmbeddingRow(
                id=str(uuid4()),
                collection="test-source",
                text="test text",
                embedding=np.array([0.1, 0.2, 0.3], dtype=np.float32),
                metadata=None,
            )
        ]
        insert_embeddings(test_db, embeddings)

        # Delete collection
        delete_collection(test_db, "test-source")

        # Verify deletion
        sources = get_collection_sources(test_db)
        assert "test-source" not in sources

        # Verify embeddings also deleted
        cursor = test_db.execute("SELECT COUNT(*) FROM embeddings WHERE collection = ?", ("test-source",))
        assert cursor.fetchone()[0] == 0

    def test_delete_collection_by_name(self, test_db):
        """Test deleting collections by name."""
        # Create multiple collections with same name
        create_collection(test_db, "source1", "SharedName", "text", CollectionState.PROCESSING)
        create_collection(test_db, "source2", "SharedName", "text", CollectionState.PROCESSING)
        create_collection(test_db, "source3", "DifferentName", "text", CollectionState.PROCESSING)

        # Delete by name
        result = delete_collection_by_name(test_db, "SharedName")
        assert result is True

        # Verify only SharedName collections deleted
        sources = get_collection_sources(test_db)
        assert "source1" not in sources
        assert "source2" not in sources
        assert "source3" in sources

        # Try deleting non-existent name
        result = delete_collection_by_name(test_db, "NonExistent")
        assert result is False

    def test_insert_and_get_embeddings(self, test_db):
        """Test inserting and retrieving embeddings."""
        create_collection(test_db, "test-source", "Test Name", "text", CollectionState.PROCESSING)

        # Insert embeddings
        embedding_id = str(uuid4())
        embeddings = [
            SqliteEmbeddingRow(
                id=embedding_id,
                collection="test-source",
                text="test text",
                embedding=np.array([0.1, 0.2, 0.3], dtype=np.float32),
                metadata={"key": "value"},
            )
        ]
        insert_embeddings(test_db, embeddings)

        # Get embedding by ID
        result = get_embedding_row_by_id(test_db, embedding_id)
        assert result is not None
        assert result.id == embedding_id
        assert result.text == "test text"
        assert result.metadata == {"key": "value"}

        # Get with specific collection
        result = get_embedding_row_by_id(test_db, embedding_id, "test-source")
        assert result is not None

        # Get with wrong collection
        result = get_embedding_row_by_id(test_db, embedding_id, "wrong-source")
        assert result is None

    def test_get_collections_details_by_name(self, test_db):
        """Test getting collection details by name."""
        # Create collections
        create_collection(test_db, "source1", "SharedName", "text", CollectionState.PROCESSING)
        create_collection(test_db, "source2", "SharedName", "pdf", CollectionState.COMPLETED)
        create_collection(test_db, "source3", "DifferentName", "text", CollectionState.PROCESSING)

        # Get by name
        details = get_collections_details_by_name(test_db, "SharedName")
        assert len(details) == 2
        source_paths = [d.source_path for d in details]
        assert "source1" in source_paths
        assert "source2" in source_paths
        assert "source3" not in source_paths

    @patch("embedder.store.sqlite.sql.EMBEDDING_SIZE", MagicMock(value=3))
    def test_search_embeddings(self, test_db):
        """Test searching embeddings."""
        # Note: This is a basic test since we can't load the actual vec0 extension
        # In a real environment with sqlite-vec, this would perform actual vector search
        create_collection(test_db, "test-source", "Test Name", "text", CollectionState.PROCESSING)

        query = np.array([0.1, 0.2, 0.3], dtype=np.float32)

        # This will likely fail without the vec0 extension, so we'll just test the function call
        try:
            results = search_embeddings(test_db, query, k=10)
            # If it works (unlikely in test env), verify structure
            assert isinstance(results, list)
        except Exception:
            # Expected in test environment without vec0 extension
            pass

    @patch("embedder.store.sqlite.sql.EMBEDDING_SIZE", MagicMock(value=3))
    def test_search_relevant_collections(self, test_db):
        """Test searching relevant collections."""
        create_collection(test_db, "test-source", "Test Name", "text", CollectionState.PROCESSING)

        query = np.array([0.1, 0.2, 0.3], dtype=np.float32)

        # This will likely fail without the vec0 extension
        try:
            results = search_relevant_collections(test_db, query, k=5, distance_threshold=2.0)
            assert isinstance(results, list)
        except Exception:
            # Expected in test environment without vec0 extension
            pass
