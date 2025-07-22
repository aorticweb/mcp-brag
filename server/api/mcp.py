from dataclasses import dataclass
from typing import List

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from common.config.field import env_field, int_env_field
from common.log import get_logger
from embedder.read_write.bulk_queue import BulkQueue
from embedder.store.store import DataSourceMap
from server.api.middleware import MCPErrorMiddleware
from server.api.routes import ROUTES
from server.api.tools import TOOLS
from server.constants import INSTRUCTIONS
from server.shared import (  # noqa: F401
    global_data_source_map,
    global_download_bulk_queue,
    global_download_manager,
    global_embedder_manager,
    global_embedder_read_queue,
    global_embedder_write_queue,
    global_ingestion_state_manager,
    global_transcription_manager,
    global_transcription_queue,
)
from server.thread_managers.download_manager import DownloadManager
from server.thread_managers.transcription_manager import (
    TranscriptionTask,
    TranscriptionThreadManager,
)
from server.workers.ingestion_state_manager import SourceIngestionProgressManager
from transcriber import ParakeetProvider

logger = get_logger(__name__)


@dataclass
class MCPConfig:
    host: str = env_field("MCP_HOST", "localhost")
    port: int = int_env_field("MCP_PORT", 8000)


MCP_NAME = "Corpus"

cfg = MCPConfig()
mcp: FastMCP = FastMCP(MCP_NAME, INSTRUCTIONS.value, host=cfg.host, port=cfg.port)


def initialize_dependencies(
    embedder_read_queue: BulkQueue,
    embedder_write_queue: BulkQueue,
    embedder_manager,
    data_source_map: DataSourceMap,
    ingestion_state_manager: SourceIngestionProgressManager,
):
    """Initialize the global dependencies for the tools.

    Args:
        embedder_read_queue: Queue for submitting text for embedding
        embedder_write_queue: Queue for storing embeddings
        data_source_map: Map of data sources for storage and retrieval
    """
    global_embedder_read_queue.set(embedder_read_queue)
    global_embedder_write_queue.set(embedder_write_queue)
    global_embedder_manager.set(embedder_manager)
    global_data_source_map.set(data_source_map)
    global_ingestion_state_manager.set(ingestion_state_manager)
    # Initialize transcription infrastructure
    transcription_queue = BulkQueue[TranscriptionTask](maxsize=1000)
    transcription_manager = TranscriptionThreadManager(
        transcription_queue=transcription_queue,
        embedder_read_queue=embedder_read_queue,
        transcription_provider=ParakeetProvider(),
        ingestion_state_manager=ingestion_state_manager,
    )
    global_transcription_queue.set(transcription_queue)
    global_transcription_manager.set(transcription_manager)

    # Initialize YouTube download infrastructure
    download_bulk_queue = BulkQueue[str](maxsize=1000)
    download_manager = DownloadManager(
        download_queue=download_bulk_queue,
        transcription_queue=transcription_queue,
        ingestion_state_manager=ingestion_state_manager,
    )
    global_download_bulk_queue.set(download_bulk_queue)
    global_download_manager.set(download_manager)

    download_bulk_queue.set_wake_consumer_function(download_manager.ensure_running)
    transcription_queue.set_wake_consumer_function(transcription_manager.ensure_running)
    embedder_read_queue.set_wake_consumer_function(global_embedder_manager.get().ensure_running)

    initialize_mcp_tools(mcp)
    initialize_mcp_routes(mcp)


def initialize_mcp_tools(mcp: FastMCP):
    for tool in TOOLS:
        mcp._tool_manager.add_tool(tool)


def initialize_mcp_routes(mcp: FastMCP):
    for route in ROUTES:
        mcp._additional_http_routes.append(route)


def get_mcp_middleware() -> List[Middleware]:
    return [
        Middleware(MCPErrorMiddleware),
        # TODO: figure out CORS middleware setup
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Disable CORS restrictions
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        ),
    ]
