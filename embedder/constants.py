"""Constants used throughout the embedder module."""

from datetime import timedelta
from pathlib import Path

from common.config.constant import Constant

APP_DIR = Constant(f"{Path.home()}/.mcp-brag", env_var="MCP_RAG_APP_DIR")


def app_dir_path() -> Path:
    return Path(APP_DIR.value)


# Vectorizer configuration
VECTORIZER_MODEL_PATH = Constant("sentence-transformers/all-MiniLM-L6-v2", env_var="VECTORIZER_MODEL_PATH")

# Bulk queue configuration
BULK_QUEUE_FULL_SLEEP_TIME = Constant(0.1, env_var="BULK_QUEUE_FULL_SLEEP_TIME")
BULK_QUEUE_FULL_RETRY_COUNT = Constant(100, env_var="BULK_QUEUE_FULL_RETRY_COUNT")
ASYNC_QUEUE_BATCH_SIZE = Constant(100, env_var="ASYNC_QUEUE_BATCH_SIZE")
ASYNC_QUEUE_READ_SLEEP = Constant(timedelta(milliseconds=50), env_var="ASYNC_QUEUE_READ_SLEEP")
ASYNC_QUEUE_MAX_SIZE = Constant(100000, env_var="ASYNC_QUEUE_MAX_SIZE")


# Embedding configuration
EMBEDDING_SIZE = Constant(384, env_var="EMBEDDING_SIZE")

# Database configuration
SQLITE_DB_LOCATION = Constant(str(app_dir_path() / "data/sqlite_db_files/embeddings.db"), env_var="SQLITE_DB_LOCATION")
