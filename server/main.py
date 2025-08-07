import threading
import time
from collections import defaultdict
from enum import Enum
from typing import Tuple

from fastmcp import FastMCP

from common.log import get_logger
from embedder.constants import ASYNC_QUEUE_MAX_SIZE, app_dir_path
from embedder.embed import Embedder
from embedder.read_write.bulk_queue import BulkQueue
from embedder.store import VectorStoreType, get_vector_store
from embedder.store.store import CollectionState, DataSourceMap
from embedder.text import TextInput
from server.api.mcp import get_mcp_middleware, initialize_dependencies, mcp
from server.shared import get_ingestion_state_manager
from server.thread_managers.embedder_manager import EmbedderThreadManager
from server.workers.ingestion_state_manager import (
    IngestionPhase,
    SourceIngestionProgressManager,
)
from embedder.constants import CONFIG_FILE
import yaml

logger = get_logger(__name__)


def ensure_app_dir_exists():
    """
    Ensure the application directory exists with proper permissions.
    Creates the directory if it doesn't exist.
    """
    app_dir = app_dir_path()

    try:
        # Create directory with parents if it doesn't exist
        app_dir.mkdir(parents=True, exist_ok=True)

        # Verify permissions by creating a test file
        test_file = app_dir / ".permission_test"
        try:
            # Test write permission
            test_file.write_text("test")
            # Test read permission
            test_file.read_text()
            # Test delete permission
            test_file.unlink()

            logger.info(f"App directory '{app_dir}' exists with proper permissions")
            config_file = app_dir / "config.yaml"
            if not config_file.exists():
                config_file.write_text("")
        except Exception as e:
            logger.error(f"App directory '{app_dir}' exists but lacks proper permissions: {e}")
            raise PermissionError(f"Insufficient permissions for app directory '{app_dir}': {e}")

    except Exception as e:
        logger.error(f"Failed to create or access app directory '{app_dir}': {e}")
        raise


def run_embedder(embedder: Embedder):
    """
    Run embedder in continuous loop

    Args:
        embedder: Embedder instance to run
    """
    logger.info("Starting embedder")
    while True:
        embedder.iter()


def start_embedder_thread(
    ingestion_state_manager: SourceIngestionProgressManager,
) -> Tuple[BulkQueue, BulkQueue, EmbedderThreadManager]:
    """
    Start embedder thread with associated queues

    Args:
        ingestion_state_manager: Manager for tracking ingestion progress

    Returns:
        Tuple[BulkQueue, BulkQueue, EmbedderThreadManager]: Read queue, write queue, and thread manager
    """
    # setup transport
    read_queue = BulkQueue[TextInput](maxsize=ASYNC_QUEUE_MAX_SIZE.value)
    write_queue = BulkQueue[TextInput](maxsize=ASYNC_QUEUE_MAX_SIZE.value)

    # Create thread manager
    manager = EmbedderThreadManager(read_queue, write_queue, ingestion_state_manager)
    manager.ensure_running()

    return read_queue, write_queue, manager


def run_continuous_storage(data_source_map: DataSourceMap, read_queue: BulkQueue[TextInput]):
    """
    Continuously process and store embedded text inputs

    Args:
        data_source_map: Map of data sources for storage
        read_queue: Queue to read embedded text inputs from
    """
    while True:
        text_inputs = read_queue.get_many(1000)
        if len(text_inputs) == 0:
            time.sleep(1)
            continue
        logger.debug(f"Received {len(text_inputs)} text inputs for storage")

        valid_text_inputs_by_source = defaultdict(list)
        for text_input in text_inputs:
            if not isinstance(text_input, TextInput) or "source" not in text_input._meta:
                logger.warning(f"Received invalid text input: {text_input}")
                continue
            valid_text_inputs_by_source[text_input._meta["source"]].append(text_input)

        for source, valid_text_inputs in valid_text_inputs_by_source.items():
            if not data_source_map.exists(source):
                logger.debug(f"Creating new data source: {source}")
                data_source_map.create(source, valid_text_inputs[0]._meta["source_type"])

            logger.debug(f"Storing {len(valid_text_inputs)} text inputs for source: {source}")
            data_source_map.get(source).add_batch(valid_text_inputs)
            ingestion_state_manager = get_ingestion_state_manager()
            ingestion_state_manager.increment_phase_progress(source, IngestionPhase.STORING, len(valid_text_inputs))
            if (ingestion_state_manager.get_phase_percentage(source, IngestionPhase.STORING) or 0) >= 100:
                ingestion_state_manager.mark_as_completed(source)
                data_source_map.set_state(source, CollectionState.COMPLETED)


def start_vec_storage_thread(store: DataSourceMap, read_queue: BulkQueue):
    """
    Start vector storage thread in background

    Args:
        store: DataSourceMap for vector storage
        read_queue: Queue to read embedded vectors from
    """
    storage_thread = threading.Thread(target=run_continuous_storage, args=(store, read_queue), daemon=True)
    storage_thread.start()


class MCPMode(str, Enum):
    SSE = "sse"
    STREAMABLE_HTTP = "streamable-http"


def run_mcp_server(mcp: FastMCP, mode: MCPMode = MCPMode.SSE):
    """
    Run MCP server with specified transport mode

    Args:
        mcp: FastMCP server instance
        mode: Server mode (SSE or STREAMABLE_HTTP)
    """
    print(f"Running MCP server in {mode.value} mode")
    middleware = get_mcp_middleware()
    mcp.run(mode.value, middleware=middleware)


def main():
    """Main entry point for the server"""
    # Ensure app directory exists with proper permissions
    ensure_app_dir_exists()

    ingestion_state_manager = SourceIngestionProgressManager()
    # Start embedder in background thread
    embedder_read_queue, embedder_write_queue, embedder_manager = start_embedder_thread(ingestion_state_manager)

    # Create data source map instance
    # TODO: make this configurable
    data_source_map = get_vector_store(VectorStoreType.SQLITE)

    # Start continuous storage in background thread
    start_vec_storage_thread(data_source_map, embedder_write_queue)

    # Initialize tools dependencies
    initialize_dependencies(
        embedder_read_queue, embedder_write_queue, embedder_manager, data_source_map, ingestion_state_manager
    )
    logger.info("MCP Brag RAG server initialized successfully")
    run_mcp_server(mcp, MCPMode.SSE)


if __name__ == "__main__":
    main()
