import asyncio
import os
from typing import List

from starlette.requests import Request
from starlette.routing import Route

from common.log import get_logger
from server.api.config import all_configs, edit_config
from server.api.internal import (
    _deep_search,
    _delete_data_source,
    _delete_data_sources_by_name,
    _get_collection_ingestion_status,
    _get_data_source_stats,
    _get_system_status,
    _list_data_sources_files,
    _list_data_sources_files_by_name,
    _most_relevant_files,
    _process_file_async,
    _process_url,
    _search_files,
)
from server.api.response import JSONResponse
from server.constants import INGESTION_PROCESS_MAX_FILE_PATHS
from server.error import MCPError
from server.shared import ActiveDataSources

logger = get_logger(__name__)


def expand_file_path(file_path: str) -> List[str]:
    """Expand a file path to a list of all files.

    If file_path is a single file, return [file_path].
    If it's a directory, recursively find all files in the directory and subdirectories.

    Args:
        file_path: Path to a file or directory

    Returns:
        List of file paths
    """
    if os.path.isfile(file_path):
        return [file_path]
    elif os.path.isdir(file_path):
        file_paths = []
        for root, dirs, files in os.walk(file_path):
            for file in files:
                file_paths.append(os.path.join(root, file))
        return file_paths
    else:
        raise MCPError(f"Invalid file path: {file_path}", code=400)


async def process_file_async_api(request: Request) -> JSONResponse:
    """
    API endpoint to process files asynchronously for embedding

    Args:
        request: HTTP request containing file_path and optional source_name

    Returns:
        JSONResponse: Success status with 201 status code
    """
    data = await request.json()
    file_path = data["file_path"]
    file_paths = expand_file_path(file_path)
    if len(file_paths) > INGESTION_PROCESS_MAX_FILE_PATHS.value:
        raise MCPError(
            f"Too many files: {len(file_paths)} in path {file_path} (max = {INGESTION_PROCESS_MAX_FILE_PATHS.value})",
            code=400,
        )
    asyncio.get_event_loop().run_in_executor(None, _process_file_async, file_paths, data.get("source_name"))
    return JSONResponse({"status": "success"}, status_code=201)


async def process_url_async_api(request: Request) -> JSONResponse:
    """
    API endpoint to process URLs asynchronously for downloading and embedding

    Args:
        request: HTTP request containing url and optional source_name

    Returns:
        JSONResponse: Success status with confirmation message
    """
    data = await request.json()
    url = data.get("url")
    if not url:
        raise MCPError("url is required", code=400)
    _process_url(url, data.get("source_name"))
    return JSONResponse({"status": "success", "message": f"URL {url} added to download queue"}, status_code=201)


async def search_file_manual_api(request: Request) -> JSONResponse:
    """
    API endpoint to search files using vector similarity

    Args:
        request: HTTP request containing query and optional offset

    Returns:
        JSONResponse: Search results with matching text snippets
    """
    data = await request.json()
    query = data["query"]
    offset = data.get("offset", 0)
    return JSONResponse(_search_files(query, offset))


async def deep_search_api(request: Request) -> JSONResponse:
    """
    API endpoint for deep search across specific sources

    Args:
        request: HTTP request containing query and sources list

    Returns:
        JSONResponse: Extended search results from specified sources
    """
    data = await request.json()
    query = data["query"]
    sources = data["sources"]
    return JSONResponse(_deep_search(query, sources))


async def most_relevant_files_api(request: Request) -> JSONResponse:
    """
    API endpoint to find most relevant files for a query

    Args:
        request: HTTP request containing query

    Returns:
        JSONResponse: List of files ranked by relevance
    """
    data = await request.json()
    query = data["query"]
    return JSONResponse(_most_relevant_files(query))


async def get_system_status_api(_: Request) -> JSONResponse:
    """
    API endpoint to check system health status

    Returns:
        JSONResponse: System operational status
    """
    data = _get_system_status()
    return JSONResponse(data)


async def health_check_api(_: Request) -> JSONResponse:
    """
    API endpoint for basic health check

    Returns:
        JSONResponse: Simple ok status
    """
    return JSONResponse(
        {
            "status": "ok",
        }
    )


async def set_config_api(request: Request) -> JSONResponse:
    """
    API endpoint to update configuration settings

    Args:
        request: HTTP request containing config_name and config_value

    Returns:
        JSONResponse: Updated configuration data
    """
    data = await request.json()
    config_name = data["config_name"]
    config_value = data["config_value"]
    c = edit_config(config_name, config_value)
    payload = {
        "status": "ok",
        "data": c,
    }
    return JSONResponse(payload)


async def get_config_api(_: Request) -> JSONResponse:
    """
    API endpoint to retrieve all configuration settings

    Returns:
        JSONResponse: All current configurations
    """
    return JSONResponse({"status": "ok", "data": all_configs()})


async def get_data_sources_api(request: Request) -> JSONResponse:
    """
    API endpoint to retrieve data sources with optional filtering

    Args:
        request: HTTP request with optional query params source_name or source

    Returns:
        JSONResponse: Data source statistics and file listings
    """
    source_name = request.query_params.get("source_name")
    source = request.query_params.get("source")
    if source_name and source:
        raise MCPError("Source name and source cannot be provided together", code=400)
    if source_name:
        return JSONResponse(_list_data_sources_files_by_name(source_name))
    if source:
        return JSONResponse(_get_data_source_stats(source))
    return JSONResponse(_list_data_sources_files())


async def get_ingestion_status_api(request: Request) -> JSONResponse:
    """
    API endpoint to check ingestion progress for a data source

    Args:
        request: HTTP request containing source identifier

    Returns:
        JSONResponse: Ingestion status and progress information
    """
    data = await request.json()
    source = data["source"]
    return JSONResponse(_get_collection_ingestion_status(source))


async def delete_data_source_api(request: Request) -> JSONResponse:
    """
    API endpoint to delete a specific data source

    Args:
        request: HTTP request containing source identifier

    Returns:
        JSONResponse: Deletion confirmation status
    """
    data = await request.json()
    source = data["source"]
    return JSONResponse(_delete_data_source(source))


async def delete_data_sources_by_name_api(request: Request) -> JSONResponse:
    """
    API endpoint to delete all data sources with a specific name

    Args:
        request: HTTP request containing source_name

    Returns:
        JSONResponse: Deletion confirmation status
    """
    data = await request.json()
    source_name = data["source_name"]
    return JSONResponse(_delete_data_sources_by_name(source_name))


# TODO:
# persist active data sources to the DB
async def mark_data_sources_as_active_api(request: Request) -> JSONResponse:
    """
    API endpoint to mark data sources as active for searching

    Args:
        request: HTTP request containing source_paths list

    Returns:
        JSONResponse: Updated list of active data sources
    """
    data = await request.json()
    source_paths = data["source_paths"]

    with ActiveDataSources() as c:
        if c.active_data_sources is None:
            c.active_data_sources = set()
        validated_source_paths = c.validate_data_sources(source_paths)
        for source_path in validated_source_paths:
            if source_path in c.active_data_sources:
                continue
            c.active_data_sources.add(source_path)

    return JSONResponse({"status": "ok", "active_data_sources": list(c.active_data_sources)})


async def mark_data_sources_as_inactive_api(request: Request) -> JSONResponse:
    """
    API endpoint to mark data sources as inactive

    Args:
        request: HTTP request containing source_paths list

    Returns:
        JSONResponse: Updated list of active data sources
    """
    data = await request.json()
    source_paths = data.get("source_paths")
    if source_paths is None:
        raise MCPError("source_paths is required", code=400)
    with ActiveDataSources() as c:
        if c.active_data_sources is None:
            c.active_data_sources = set()
        for source_path in source_paths:
            if source_path not in c.active_data_sources:
                continue
            c.active_data_sources.remove(source_path)
    return JSONResponse({"status": "ok", "active_data_sources": list(c.active_data_sources)})


async def get_active_data_sources_api(_: Request) -> JSONResponse:
    """
    API endpoint to retrieve all currently active data sources

    Returns:
        JSONResponse: List of active data source paths
    """
    c = ActiveDataSources()
    active_data_sources = list(c.active_data_sources) if c.active_data_sources is not None else []
    return JSONResponse({"status": "ok", "active_data_sources": active_data_sources})


ROUTES = [
    Route("/manual/config", get_config_api, methods=["GET"]),
    Route("/manual/config", set_config_api, methods=["POST"]),
    Route("/manual/data_sources", get_data_sources_api, methods=["GET"]),
    Route("/manual/delete_data_source", delete_data_source_api, methods=["POST"]),
    Route("/manual/delete_data_sources_by_name", delete_data_sources_by_name_api, methods=["POST"]),
    Route("/manual/health", health_check_api, methods=["GET"]),
    Route("/manual/ingestion_status", get_ingestion_status_api, methods=["POST"]),
    Route("/manual/process_file_async", process_file_async_api, methods=["POST"]),
    Route("/manual/process_url_async", process_url_async_api, methods=["POST"]),
    Route("/manual/search_file", search_file_manual_api, methods=["POST"]),
    Route("/manual/system_status", get_system_status_api, methods=["GET"]),
    Route("/manual/active_data_sources", get_active_data_sources_api, methods=["GET"]),
    Route("/manual/mark_data_sources_as_active", mark_data_sources_as_active_api, methods=["POST"]),
    Route("/manual/mark_data_sources_as_inactive", mark_data_sources_as_inactive_api, methods=["POST"]),
    # Not documented
    Route("/manual/deep_search", deep_search_api, methods=["POST"]),
    Route("/manual/most_relevant_files", most_relevant_files_api, methods=["POST"]),
]
