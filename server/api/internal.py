import time
from typing import Any, Dict, List, Optional

from common.log import get_logger
from embedder.store.store import USER_QUERY_SOURCE, CollectionState
from server.api.search import SearchResult, most_relevant_sources, search
from server.constants import (
    DEEP_SEARCH_RESULT_LIMIT,
    MAX_SOURCES_IN_DEEP_SEARCH,
    SEARCH_RESULT_LIMIT,
)
from server.read import ReaderFactory, SourceType
from server.shared import (
    ActiveDataSources,
    check_dependencies,
    get_data_source_map,
    get_download_bulk_queue,
    get_embedder_read_queue,
    get_ingestion_state_manager,
    get_transcription_queue,
)
from server.workers.embedding import generate_embeddings_for_file
from server.workers.ingestion_state_manager import IngestionPhase

logger = get_logger(__name__)


def _process_file_async(file_paths: List[str], source_name: Optional[str] = None):
    """
    Process files asynchronously for embedding and storage in vector database

    Args:
        file_paths: List of file paths to process
        source_name: Optional name to group files under
    """
    transcription_queue = get_transcription_queue()
    embedder_read_queue = get_embedder_read_queue()
    data_source_map = get_data_source_map()

    for file_path in file_paths:
        if data_source_map.exists(file_path):
            logger.debug(f"Data source {file_path} already exists, deleting it prior to ingestion")
            _delete_data_source(file_path)

        try:
            reader = ReaderFactory.create_reader(file_path)
            # Set ingestion initial state
            progress_manager = get_ingestion_state_manager()
            progress_manager.create_state(
                file_path,
                data_source_map.success_ingestion_process_callback(file_path),
                data_source_map.fail_ingestion_process_callback(file_path),
            )
            progress_manager.add_phase(file_path, IngestionPhase.INITIALIZATION, total=1)
            # Create collection in vector store
            data_source_map.create(file_path, reader.source_type(), source_name, CollectionState.PROCESSING)
            # Update ingestion state to embedding phase
            progress_manager.increment_phase_progress(file_path, IngestionPhase.INITIALIZATION, 1)

            # Generate embeddings for file
            generate_embeddings_for_file(file_path, embedder_read_queue, transcription_queue, progress_manager)

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            data_source_map.set_state(file_path, CollectionState.FAILED)
            continue


def _process_url(url: str, source_name: Optional[str] = None):
    """
    Process URL content for downloading and embedding

    Args:
        url: URL to process (currently supports YouTube)
        source_name: Optional name to group URL content under
    """
    download_queue = get_download_bulk_queue()

    data_source_map = get_data_source_map()
    if data_source_map.exists(url):
        logger.debug(f"Data source {url} already exists, deleting it prior to ingestion")
        _delete_data_source(url)

    # Set ingestion initial state
    progress_manager = get_ingestion_state_manager()
    progress_manager.create_state(
        url,
        data_source_map.success_ingestion_process_callback(url),
        data_source_map.fail_ingestion_process_callback(url),
    )
    progress_manager.add_phase(url, IngestionPhase.INITIALIZATION, total=1)
    # Add the URL to the download queue
    download_queue.put_many([url])
    progress_manager.increment_phase_progress(url, IngestionPhase.INITIALIZATION, 1)
    # todo:
    # support non-youtube urls
    data_source_map.create(url, SourceType.YOUTUBE_TRANSCRIPTION, source_name, CollectionState.PROCESSING)


def _active_data_sources() -> Optional[List[str]]:
    """
    Get list of currently active data sources

    Returns:
        Optional[List[str]]: List of active data source names or None if empty
    """
    with ActiveDataSources() as c:
        sources = (
            list(c.active_data_sources.copy())
            if c.active_data_sources is not None and len(c.active_data_sources) > 0
            else None
        )
        return sources


def _post_process_search_results(query: str, search_results: List[SearchResult], search_time: float) -> Dict[str, Any]:
    """
    Format search results into a standardized response format

    Args:
        query: Original search query
        search_results: List of search results from vector search
        search_time: Time taken to perform search in seconds

    Returns:
        Dict[str, Any]: Formatted response with status, query, results count, time, and results
    """
    # Format results for better readability
    formatted_results = []
    for result in search_results:
        formatted_results.append(
            {
                "text": result.text,
                "source": result.source,
                "distance": float(result.distance),
            }
        )

    return {
        "status": "success",
        "query": query,
        "results_count": len(formatted_results),
        "search_time_seconds": f"{search_time:.3f}",
        "results": formatted_results,
    }


def _search_files(query: str, offset: int = 0) -> Dict[str, Any]:
    """
    Search files using vector similarity search with pagination

    Args:
        query: Search query text
        offset: Pagination offset for results

    Returns:
        Dict[str, Any]: Search results with status and formatted matches
    """
    embedder_read_queue = get_embedder_read_queue()
    data_source_map = get_data_source_map()

    if not query.strip():
        return {"status": "error", "error": "Query cannot be empty"}

    sources = _active_data_sources()

    start_time = time.time()
    search_results = search(query, embedder_read_queue, data_source_map, sources, SEARCH_RESULT_LIMIT.value, offset)
    search_time = time.time() - start_time
    search_results = search_results[offset : offset + SEARCH_RESULT_LIMIT.value]

    return _post_process_search_results(query, search_results, search_time)


def _deep_search(query: str, sources: List[str]) -> Dict[str, Any]:
    """
    Perform deep search across specific sources with higher result limit

    Args:
        query: Search query text
        sources: List of specific source identifiers to search within

    Returns:
        Dict[str, Any]: Deep search results with extended match limits
    """
    embedder_read_queue = get_embedder_read_queue()
    data_source_map = get_data_source_map()

    if not query.strip():
        return {"status": "error", "error": "Query cannot be empty"}

    if len(sources) > MAX_SOURCES_IN_DEEP_SEARCH.value:
        return {
            "status": "error",
            "error": f"Too many sources: {len(sources)} (max = {MAX_SOURCES_IN_DEEP_SEARCH.value})",
        }

    start_time = time.time()
    search_results = search(
        query,
        embedder_read_queue,
        data_source_map,
        sources,
        DEEP_SEARCH_RESULT_LIMIT.value,
    )
    search_time = time.time() - start_time
    search_results = search_results[: DEEP_SEARCH_RESULT_LIMIT.value]

    return _post_process_search_results(query, search_results, search_time)


def _most_relevant_files(query: str) -> Dict[str, Any]:
    """
    Find most relevant files based on query similarity

    Args:
        query: Search query text

    Returns:
        Dict[str, Any]: List of most relevant sources ranked by relevance
    """
    embedder_read_queue = get_embedder_read_queue()
    data_source_map = get_data_source_map()

    sources = _active_data_sources()
    start_time = time.time()
    most_relevant_sources_list = most_relevant_sources(
        query, embedder_read_queue, data_source_map, sources, SEARCH_RESULT_LIMIT.value
    )
    search_time = time.time() - start_time
    return {
        "status": "success",
        "most_relevant_sources": most_relevant_sources_list,
        "search_time_seconds": f"{search_time:.3f}",
    }


def _get_data_source_stats(source: str) -> Dict[str, Any]:
    """
    Get statistics for a specific data source

    Args:
        source: Data source identifier

    Returns:
        Dict[str, Any]: Statistics including vector count and file info
    """
    data_source_map = get_data_source_map()
    stats = data_source_map.get_source_stats(source)
    return {
        "status": "success",
        "total_files": 1,
        "total_vectors": stats.vector_count,
        "file": [stats.to_dict()],
    }


def _list_data_sources_files() -> Dict[str, Any]:
    """
    List all data source files with their statistics

    Returns:
        Dict[str, Any]: List of all files with total counts and individual stats
    """
    data_source_map = get_data_source_map()

    sources = data_source_map.list_sources()
    stats = data_source_map.get_sources_stats()

    # Filter out user query source and empty sources
    file_sources = []
    total_vectors = 0
    for source in sources:
        if source == USER_QUERY_SOURCE or source not in stats:
            continue
        source_stats = stats[source]
        file_sources.append(source_stats.to_dict())
        total_vectors += source_stats.vector_count

    return {
        "status": "success",
        "total_files": len(file_sources),
        "total_vectors": total_vectors,
        "files": file_sources,
    }


def _list_data_sources_files_by_name(source_name: str) -> Dict[str, Any]:
    """
    List data source files filtered by source name

    Args:
        source_name: Name of source to filter by

    Returns:
        Dict[str, Any]: Filtered list of files with statistics
    """
    data_source_map = get_data_source_map()
    stats = data_source_map.get_source_stats_by_name(source_name)
    file_sources = []
    total_vectors = 0
    for s in stats:
        file_sources.append(s.to_dict())
        total_vectors += s.vector_count

    return {
        "status": "success",
        "total_files": len(file_sources),
        "total_vectors": total_vectors,
        "files": file_sources,
    }


def _get_system_status() -> Dict[str, Any]:
    """
    Check system health and operational status

    Returns:
        Dict[str, Any]: System status and health information
    """
    check_dependencies()
    return {
        "status": "success",
        "system_health": "operational",
    }


def _delete_data_source(source: str) -> Dict[str, Any]:
    """
    Delete a specific data source from the system

    Args:
        source: Data source identifier to delete

    Returns:
        Dict[str, Any]: Deletion status and confirmation message
    """
    data_source_map = get_data_source_map()
    found = data_source_map.delete(source)
    return {
        "status": "success",
        "message": f"Data source {source} deleted successfully" if found else f"Data source {source} not found",
        "data_source_was_found": found,
    }


def _delete_data_sources_by_name(source_name: str) -> Dict[str, Any]:
    """
    Delete all data sources matching a specific name

    Args:
        source_name: Name of sources to delete

    Returns:
        Dict[str, Any]: Deletion status and confirmation message
    """
    data_source_map = get_data_source_map()
    found = data_source_map.delete_by_name(source_name)
    return {
        "status": "success",
        "message": f"Data sources with name {source_name} deleted successfully"
        if found
        else f"No data source with name {source_name} were found",
        "data_sources_were_found": found,
    }


def _get_collection_ingestion_status(source: str) -> Dict[str, Any]:
    """
    Get ingestion status and progress for a data source

    Args:
        source: Data source identifier

    Returns:
        Dict[str, Any]: Ingestion status, progress, and related information
    """
    data_source_map = get_data_source_map()
    stats = data_source_map.get_source_stats(source)
    if stats.status == CollectionState.NOT_FOUND:
        return {
            "status": "success",
            "ingestion_status": stats.status,
            "message": f"Data source {source} not found",
        }

    if stats.status == CollectionState.FAILED:
        return {
            "status": "success",
            "ingestion_status": stats.status,
            "message": f"Data source {source} failed to ingest",
        }

    if stats.status == CollectionState.COMPLETED:
        return {
            "status": "success",
            "ingestion_status": stats.status,
        }

    if stats.status == CollectionState.PROCESSING:
        progress_manager = get_ingestion_state_manager()
        progress = progress_manager.get_state(source)
        # That means the ingestion process was somehow interrupted halfway
        # there is no self recovery mechanism (yet), so we need to set the state to failed
        if progress is None:
            data_source_map.set_state(source, CollectionState.FAILED)
            return {
                "status": "success",
                "ingestion_status": CollectionState.FAILED,
                "message": f"Data source {source} failed to ingest",
            }

        return {
            "status": "success",
            "ingestion_status": stats.status,
            "progress": progress.to_dict() if progress is not None else {},
        }

    return {
        "status": "success",
        "ingestion_status": stats.status,
        "progress": 0,
        "total_chunk_count": 0,
    }
