import json
import os
import sqlite3
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np
import sqlean
import sqlite_vec

from common.log import get_logger
from common.singleton import Singleton
from embedder.constants import EMBEDDING_SIZE, SQLITE_DB_LOCATION
from embedder.store.store import CollectionState, DataSourceStats, RelevantCollection

logger = get_logger(__name__)


# from sqlean.dbapi2.Row
# sqlean is a wrapper around sqlite3 that allows for loading extensions
# the typing here is wrong but this is a workaround to avoid having
# to customize the python install to enable loading extensions
def get_sqlite_connection() -> sqlite3.Connection:
    db_location_folder = os.path.dirname(SQLITE_DB_LOCATION.value)
    if not os.path.exists(db_location_folder):
        os.makedirs(db_location_folder)

    # Use a file-based database to allow sharing between threads
    # Using WAL mode for better concurrency
    conn = sqlean.connect(SQLITE_DB_LOCATION.value, check_same_thread=False)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlean.Row
    # Enable WAL mode for better concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


class SqliteConnInstance(metaclass=Singleton):
    _connection = None
    _lock = threading.Lock()

    def __init__(self):
        pass

    @property
    def conn(self) -> sqlite3.Connection:
        """Get a shared SQLite connection with thread safety."""
        if self._connection is None:
            with self._lock:
                if self._connection is None:
                    self._connection = get_sqlite_connection()
        return self._connection


@dataclass
class SqliteEmbeddingRow:
    id: str
    collection: str
    text: str
    embedding: np.ndarray
    metadata: Optional[Dict[str, Any]]

    def to_row_dict(self) -> Dict:
        return {
            "id": self.id,
            "collection": self.collection,
            "text": self.text,
            "embedding": format_embedding_for_sqlite(self.embedding),
            "metadata": json.dumps(self.metadata) if self.metadata else "{}",
        }

    @staticmethod
    def from_row(row: Dict) -> "SqliteEmbeddingRow":
        return SqliteEmbeddingRow(
            id=row["id"],
            collection=row["collection"],
            text=row["text"],
            embedding=np.array(json.loads(row["embedding"]), dtype=np.float32),
            metadata=json.loads(row["metadata"]) if row["metadata"] and row["metadata"] != "{}" else None,
        )


@dataclass
class SqliteEmbeddingRowWithDistance(SqliteEmbeddingRow):
    distance: float

    @staticmethod
    def from_row(row: Dict) -> "SqliteEmbeddingRowWithDistance":
        return SqliteEmbeddingRowWithDistance(
            id=row["id"],
            collection=row["collection"],
            text=row["text"],
            embedding=np.array(json.loads(row["embedding"]), dtype=np.float32),
            metadata=json.loads(row["metadata"]) if row["metadata"] and row["metadata"] != "{}" else None,
            distance=row["distance"],
        )


@dataclass
class SqliteRelevantCollectionRow:
    collection: str
    min_distance: float
    avg_distance: float
    count: int

    @staticmethod
    def from_row(row: Dict) -> "SqliteRelevantCollectionRow":
        return SqliteRelevantCollectionRow(
            collection=row["collection"],
            min_distance=row["min_distance"],
            avg_distance=row["avg_distance"],
            count=row["count"],
        )

    def to_relevant_collection(self) -> RelevantCollection:
        return RelevantCollection(
            collection=self.collection,
            min_distance=self.min_distance,
            avg_distance=self.avg_distance,
            count=self.count,
        )


def format_embedding_for_sqlite(embedding: np.ndarray) -> str:
    return "[" + ",".join(f"{x:.12f}" for x in embedding) + "]"


def format_sources_for_sqlite(sources: List[str]) -> str:
    return ",".join(f"'{source}'" for source in sources)


def create_embeddings_table(conn: sqlite3.Connection, embedding_dim: int) -> None:
    conn.execute(
        f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
                id TEXT PRIMARY KEY,
                collection TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding FLOAT[{embedding_dim}],
                metadata TEXT
            );
        """
    )


def initialize_sqlite_tables(conn: sqlite3.Connection, embedding_dim: int) -> None:
    create_embeddings_table(conn, embedding_dim)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS collections (
            id TEXT PRIMARY KEY,
            source_name TEXT,
            source_path TEXT NOT NULL,
            source_type TEXT NOT NULL,
            state TEXT NOT NULL
        );
        """
    )


def get_embedding_row_by_id(
    conn: sqlite3.Connection, id: str, collection: Optional[str] = None
) -> Optional[SqliteEmbeddingRow]:
    cursor = conn.execute(
        """
        SELECT id, collection, text, vec_to_json(embedding) as embedding, metadata
        FROM embeddings
        WHERE id = ? AND (collection = ? OR ? IS NULL)
        LIMIT 1;
        """,
        (id, collection, collection),
    )
    row = cursor.fetchone()
    if row:
        return SqliteEmbeddingRow.from_row(row)
    return None


def search_embeddings(
    conn: sqlite3.Connection, query: np.ndarray, k: int, sources: Optional[List[str]] = None
) -> List[SqliteEmbeddingRowWithDistance]:
    if sources is None or len(sources) == 0:
        sources_clause = ""
        params = [format_embedding_for_sqlite(query), k]
    else:
        sources_clause = f"AND collection IN ({','.join(['?' for _ in range(len(sources))])})"
        params = [format_embedding_for_sqlite(query), *sources, k]

    cursor = conn.execute(
        f"""
        SELECT id, collection, text, vec_to_json(embedding) as embedding, metadata, distance
        FROM embeddings
        WHERE
            embedding match ?
            AND collection <> 'user-query'
            {sources_clause}
        LIMIT ?;
        """,
        tuple(params),
    )
    rows = cursor.fetchall()
    return [SqliteEmbeddingRowWithDistance.from_row(row) for row in rows]


def search_relevant_collections(
    conn: sqlite3.Connection,
    query: np.ndarray,
    k: int,
    sources: Optional[List[str]] = None,
    distance_threshold: float = 10.0,
) -> List[SqliteRelevantCollectionRow]:
    if sources is None or len(sources) == 0:
        sources_clause = ""
        params = [format_embedding_for_sqlite(query), distance_threshold, k]
    else:
        sources_clause = f"AND collection IN ({','.join(['?' for _ in range(len(sources))])})"
        params = [format_embedding_for_sqlite(query), distance_threshold, *sources, k]
    cursor = conn.execute(
        f"""
            WITH results AS (
                SELECT
                    collection,
                    distance
                FROM embeddings
                WHERE
                    embedding MATCH ?
                    AND k = 4096
                    AND distance < ?
                    AND collection <> 'user-query'
                    {sources_clause}
                ORDER BY distance
            )
            SELECT
                collection,
                MIN(distance) AS min_distance,
                AVG(distance) AS avg_distance,
                COUNT(*) AS count
            FROM results
            GROUP BY collection
            LIMIT ?;
        """,
        tuple(params),
    )
    return [SqliteRelevantCollectionRow.from_row(row) for row in cursor.fetchall()]


def get_collection_sources(conn: sqlite3.Connection) -> List[str]:
    cursor = conn.execute(
        """
        SELECT DISTINCT source_path FROM collections;
        """
    )
    return [row["source_path"] for row in cursor.fetchall()]


def get_collections_details(conn: sqlite3.Connection, collections: Optional[List[str]] = None) -> List[DataSourceStats]:
    if collections is None:
        cursor = conn.execute(
            """
            SELECT id, source_name, source_path, source_type, state
            FROM collections
            """
        )
    else:
        cursor = conn.execute(
            """
            SELECT id, source_name, source_path, source_type, state
            FROM collections
            WHERE source_path IN (?)
            """,
            collections,
        )
    return _get_collections_details(conn, cursor)


def get_collections_details_by_name(conn: sqlite3.Connection, source_name: str) -> List[DataSourceStats]:
    cursor = conn.execute(
        """
        SELECT id, source_name, source_path, source_type, state
        FROM collections
        WHERE source_name = ?
        """,
        (source_name,),
    )
    return _get_collections_details(conn, cursor)


def _get_collections_details(conn: sqlite3.Connection, cursor: sqlite3.Cursor) -> List[DataSourceStats]:
    collections_from_db: Dict = {row["source_path"]: row for row in cursor.fetchall()}
    collection_sources = list(collections_from_db.keys())
    stats: Dict[str, Dict[str, Any]] = {}
    if collection_sources:
        placeholders = ",".join("?" * len(collection_sources))
        stats = {
            row["collection"]: dict(row)
            for row in conn.execute(
                f"""
            SELECT collection, COUNT(*) as vector_count
            FROM embeddings
            WHERE collection IN ({placeholders})
            GROUP BY collection
            """,
                collection_sources,
            ).fetchall()
        }

    collection_with_stats = []
    for collection_source, collection in collections_from_db.items():
        stat = stats.get(collection_source, {})
        collection_with_stats.append(
            DataSourceStats(
                source_name=collection["source_name"],
                source_path=collection["source_path"],
                status=collection["state"],
                vector_count=stat.get("vector_count", 0),
                dimension=EMBEDDING_SIZE.value,  # TODO: get dimension from the collection
            )
        )
    return collection_with_stats


def create_collection(
    conn: sqlite3.Connection, source_path: str, source_name: Optional[str], source_type: str, state: CollectionState
):
    conn.execute(
        """
        INSERT INTO collections (id, source_name, source_path, source_type, state) VALUES (?, ?, ?, ?, ?);
        """,
        (str(uuid4()), source_name, source_path, source_type, state),
    )
    conn.commit()


def delete_collection(conn: sqlite3.Connection, source_path: str):
    conn.execute(
        """
        DELETE FROM collections WHERE source_path = ?;
        """,
        (source_path,),
    )
    conn.execute(
        """
        DELETE FROM embeddings WHERE collection = ?;
        """,
        (source_path,),
    )
    conn.commit()


# TODO:
# we can probably optimize this an run 2 queries instead of 3
def delete_collection_by_name(conn: sqlite3.Connection, source_name: str):
    cursor = conn.execute(
        """
            SELECT COUNT(*)
            FROM collections
            WHERE source_name = ?
            """,
        (source_name,),
    )
    count = cursor.fetchone()[0]
    if count == 0:
        return False
    conn.execute(
        """
        DELETE FROM embeddings WHERE collection IN (SELECT source_path FROM collections WHERE source_name = ?);
        """,
        (source_name,),
    )
    conn.execute(
        """
        DELETE FROM collections WHERE source_name = ?;
        """,
        (source_name,),
    )
    conn.commit()
    return True


def delete_all_embeddings(conn: sqlite3.Connection):
    """Delete all embeddings.

    Args:
        conn: SQLite connection
        source_path: The collection source path
    """

    # Delete the embeddings
    conn.execute(
        """
        DROP TABLE IF EXISTS embeddings;
        """,
    )
    create_embeddings_table(conn, EMBEDDING_SIZE.value)
    conn.commit()


def update_collection_state(conn: sqlite3.Connection, source_path: str, state: CollectionState):
    conn.execute(
        """
        UPDATE collections SET state = ? WHERE source_path = ?;
        """,
        (state, source_path),
    )
    conn.commit()


def insert_embeddings(conn: sqlite3.Connection, embeddings: List[SqliteEmbeddingRow]):
    conn.executemany(
        """
        INSERT INTO embeddings (id, collection, text, embedding, metadata) VALUES (:id, :collection, :text, :embedding, :metadata);
        """,
        [embedding.to_row_dict() for embedding in embeddings],
    )
    conn.commit()
