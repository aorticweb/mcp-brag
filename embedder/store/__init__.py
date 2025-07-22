from enum import Enum

from embedder.constants import EMBEDDING_SIZE
from embedder.store.sqlite.sql import SqliteConnInstance, initialize_sqlite_tables
from embedder.store.sqlite.sqlite import SqliteDataSourceMap
from embedder.store.store import DataSourceMap


class VectorStoreType(Enum):
    SQLITE = "sqlite"


def get_vector_store(type: VectorStoreType = VectorStoreType.SQLITE) -> DataSourceMap:
    """
    Get a vector store instance based on the specified type

    Args:
        type: Type of vector store to create (default: SQLITE)

    Returns:
        DataSourceMap: Vector store instance
    """
    if type == VectorStoreType.SQLITE:
        # Initialize tables for the shared connection
        initialize_sqlite_tables(SqliteConnInstance().conn, EMBEDDING_SIZE.value)
        return SqliteDataSourceMap()
    else:
        raise ValueError(f"Unsupported vector store type: {type}")
