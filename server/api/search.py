import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, DefaultDict, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np

from common.log import get_logger
from embedder.read_write.bulk_queue import BulkQueue
from embedder.store.store import (
    USER_QUERY_SOURCE,
    DataSourceMap,
    RelevantCollection,
    TextInputWithDistance,
)
from embedder.text import TextInput
from server.constants import (
    SEARCH_CHUNK_CHARACTER_LIMIT,
    SEARCH_CHUNKS_LIMIT,
    SEARCH_CONTEXT_EXTENSION_CHARACTERS,
    SEARCH_PROCESSING_TIMEOUT_SECONDS,
)
from server.error import MCPError
from server.read import ReaderFactory
from server.read.reader import SourceType, TextChunk

logger = get_logger(__name__)

# Cache for file contents to avoid re-reading the same file multiple times
_file_content_cache: Dict[str, str] = {}


@dataclass
class SearchResult:
    """Represents a search result with its metadata.

    Attributes:
        text: The text content of the search result
        source: The source path or identifier where the content was found
        source_type: The type of source (LOCAL_TEXT_FILE or USER_QUERY)
        start_index: The starting character index in the source
        end_index: The ending character index in the source
    """

    text: str
    source: str
    source_type: SourceType
    start_index: int
    end_index: int
    distance: float


# TODO: Add testing for this function
def _get_extended_search_result_indices(
    text_inputs: List[TextInputWithDistance],
) -> List[Tuple[int, int, float]]:
    """Get the extended search result indices for a list of text inputs.

    This function takes text inputs, extends their indices by the context extension
    amount, and merges overlapping windows to avoid duplicate content.

    Args:
        text_inputs: List of TextInput objects with metadata

    Returns:
        List of tuples containing the merged extended start and end indices
    """
    if not text_inputs:
        return []

    # TODO:
    # handle non-symetric character expansion
    # to account for when we are close to the start or end of the text
    extended_indices = [
        (
            max(0, text_input._meta["start_index"] - SEARCH_CONTEXT_EXTENSION_CHARACTERS.value),
            text_input._meta["end_index"] + SEARCH_CONTEXT_EXTENSION_CHARACTERS.value,
            text_input._distance,
        )
        for text_input in text_inputs
    ]

    # Sort by start index for efficient merging
    extended_indices.sort()

    # Merge overlapping windows
    merged_indices = []
    current_start, current_end, current_distance = extended_indices[0]

    for start, end, distance in extended_indices[1:]:
        if start <= current_end:
            # Windows overlap, extend the current window
            current_end = max(current_end, end, min(current_distance, distance))
        else:
            # No overlap, save current window and start a new one
            merged_indices.append((current_start, current_end, distance))
            current_start, current_end, current_distance = start, end, distance

    # Add the final window
    merged_indices.append((current_start, current_end, current_distance))

    return merged_indices


def _get_cached_file_content(file_path: str, file_source_type: SourceType) -> Optional[str]:
    """
    Get file content from cache or read and cache it

    Args:
        file_path: Path to the file to read
        file_source_type: Type of source file to determine reader

    Returns:
        Optional[str]: File content as string, or None if file cannot be read
    """
    if file_path in _file_content_cache:
        return _file_content_cache[file_path]

    reader = ReaderFactory.create_reader(file_path)
    _file_content_cache[file_path] = reader.read()
    return _file_content_cache[file_path]


def _read_extended_file_content(
    start_index: int,
    end_index: int,
    file_path: str,
    source: str,
    file_source_type: SourceType,
    distance: float,
) -> Optional[SearchResult]:
    """
    Read extended file content from specified indices with caching

    Args:
        start_index: Starting character index to read from
        end_index: Ending character index to read to
        file_path: Path to the file to read from
        source: Source identifier for the result
        file_source_type: Type of source file
        distance: Similarity distance for the result

    Returns:
        Optional[SearchResult]: SearchResult object with the content, or None if reading fails
    """
    content = _get_cached_file_content(file_path, file_source_type)
    if content is None:
        logger.warning(f"Content is None for {file_path}")
        return None

    try:
        # Ensure indices are within bounds
        start_index = max(0, start_index)
        end_index = min(len(content), end_index)

        if start_index >= end_index:
            return None

        extracted_content = content[start_index:end_index]

        return SearchResult(
            text=extracted_content,
            source=source,
            source_type=file_source_type,
            start_index=start_index,
            end_index=end_index,
            distance=distance,
        )

    except Exception as e:
        logger.warning(f"Error extracting content from {file_path} at indices {start_index}:{end_index}: {e}")
        return None


# TODO:
# this is only used when generating embeddings for user queries
# we do not need the chunk indices
def _cut_line_into_chunks(line: str, base_index: int = 0) -> List[TextChunk]:
    """
    Split a line of text into chunks of maximum size CHUNK_CHARACTER_LIMIT

    Args:
        line: The text line to be split into chunks
        base_index: Starting index offset for the chunks (default: 0)

    Returns:
        List[TextChunk]: List of TextChunk objects containing the split text
    """
    if not line.strip():
        return []

    chunks = []
    line_length = len(line)

    if line_length <= SEARCH_CHUNK_CHARACTER_LIMIT.value:
        sanitized_text = line.strip()
        if sanitized_text:  # Only add non-empty chunks
            chunks.append(TextChunk(base_index, base_index + line_length, sanitized_text))
    else:
        # Split into chunks, trying to break at word boundaries
        current_pos = 0
        while current_pos < line_length:
            chunk_end = min(current_pos + SEARCH_CHUNK_CHARACTER_LIMIT.value, line_length)

            # Try to break at word boundary if not at the end of line
            if chunk_end < line_length:
                # Look for last space within the chunk
                last_space = line.rfind(" ", current_pos, chunk_end)
                if last_space > current_pos:
                    chunk_end = last_space

            chunk_text = line[current_pos:chunk_end].strip()
            if chunk_text:  # Only add non-empty chunks
                chunks.append(TextChunk(base_index + current_pos, base_index + chunk_end, chunk_text))

            current_pos = chunk_end
            # Skip whitespace at the beginning of next chunk
            while current_pos < line_length and line[current_pos].isspace():
                current_pos += 1

    return chunks


def _embed_user_query(query: str, embedder_read_queue: BulkQueue) -> List[str]:
    """
    Embed a user query into text inputs for the embedder queue

    Args:
        query: The user query text
        embedder_read_queue: Queue to submit text chunks for embedding

    Returns:
        List[str]: List of query IDs for tracking
    """
    logger.info(f"Embedding user query: {query}")
    if not query.strip():
        return []

    query_ids: List[str] = []
    text_inputs: List[TextInput] = []

    # Process query lines and create chunks
    for line in query.split("\n"):
        if len(query_ids) >= SEARCH_CHUNKS_LIMIT.value:
            break

        chunks = _cut_line_into_chunks(line)
        if not chunks:
            continue

        query_id = str(uuid4())
        query_ids.append(query_id)

        # Create text inputs for each chunk with metadata
        for chunk in chunks:
            ti = TextInput(
                chunk.text,
                {
                    "id": query_id,
                    "source": USER_QUERY_SOURCE,
                    "source_type": SourceType.USER_QUERY,
                    **chunk.to_dict(),
                },
                source_id=query_id,
            )
            text_inputs.append(ti)
    embedder_read_queue.put_many(text_inputs)
    logger.debug(f"Finished submitting {len(query_ids)} chunks for embedding")
    return query_ids


def _wait_for_embeddings(query_ids: List[str], data_source_map: DataSourceMap) -> bool:
    """
    Wait for query embeddings to be processed with adaptive polling

    Args:
        query_ids: List of query IDs to wait for
        data_source_map: Data source map containing the embeddings

    Returns:
        bool: True if all embeddings are ready, False if timeout occurs
    """
    # Wait for processing to complete with optimized polling
    start_time = time.time()
    check_interval = 0.01  # Start with faster polling
    max_interval = 0.5  # Maximum polling interval
    logger.debug(f"Waiting for {query_ids} embeddings to be ready")
    while time.time() - start_time < SEARCH_PROCESSING_TIMEOUT_SECONDS.value:
        # Check if all query embeddings are ready
        ready_count = sum(
            1 for query_id in query_ids if data_source_map.get_text_input_by_id(query_id, USER_QUERY_SOURCE) is not None
        )

        if ready_count == len(query_ids):
            return True

        # Adaptive polling - start fast, then slow down
        time.sleep(check_interval)
        check_interval = min(check_interval * 1.2, max_interval)

    return False


def _search_vector_in_data_source(
    vector: np.ndarray,
    data_source_map: DataSourceMap,
    sources: Optional[List[str]] = None,
    top_k: int = 5,
) -> List[SearchResult]:
    """
    Search for similar vectors in a given data source and return extended search results

    Args:
        vector: The query vector as a numpy ndarray
        data_source_map: The DataSourceMap to search within
        sources: The identifiers for the data sources to search in (e.g., file paths)
        top_k: Maximum number of top results to retrieve per document (default: 5)

    Returns:
        List[SearchResult]: List of SearchResult objects containing extended content and similarity scores
    """
    intermediate_search_results: List[TextInputWithDistance] = data_source_map.search(vector, sources, top_k)

    logger.debug(f"Search vector in data sourcse found {len(intermediate_search_results)} intermediate results")

    results_by_source: DefaultDict[str, List[TextInputWithDistance]] = defaultdict(list)
    for result in intermediate_search_results:
        results_by_source[result._meta["source"]].append(result)

    results: List[SearchResult] = []
    for source, results_for_source in results_by_source.items():
        if len(results_for_source) == 0:
            logger.debug(f"No results for {source} in loop")
            continue

        # if coming from a youtube video
        # we need to read the transcription file
        if results_for_source[0]._meta["source_type"] in [
            SourceType.YOUTUBE_TRANSCRIPTION,
            SourceType.LOCAL_AUDIO_FILE,
        ]:
            file_path = results_for_source[0]._meta["transcription_path"]
        else:
            file_path = source

        # Get extended indices and read content
        extended_indices_with_distance = _get_extended_search_result_indices(results_for_source)

        if not extended_indices_with_distance:
            logger.debug(f"No extended indices with distance for {source}")
            return []

        source_type = results_for_source[0]._meta["source_type"]

        for start_index, end_index, distance in extended_indices_with_distance:
            if source_type == SourceType.USER_QUERY:
                logger.warning(
                    f"Skipping user query for {source} ... these results should have been filtered out at the query level"
                )
                continue

            search_result = _read_extended_file_content(
                start_index, end_index, file_path, source, source_type, distance
            )
            if search_result is not None:
                results.append(search_result)

    return results


def search(
    query: str,
    embedder_read_queue: BulkQueue,
    data_source_map: DataSourceMap,
    sources: Optional[List[str]] = None,
    limit: int = 5,
    offset: int = 0,
) -> List[SearchResult]:
    """Search for relevant content based on a text query.

    Splits the query into chunks, generates embeddings, and finds matching content
    from available data sources. Uses an optimized waiting mechanism and extends
    matched content for better context.

    Args:
        query: The search query text
        embedder_read_queue: Queue to submit text chunks for embedding
        data_source_map: Data source map for searching through indexed content
        sources: List of sources to search in. If None, all sources will be searched.
        limit: Maximum number of results to return
        offset: Offset for the results

    Returns:
        List of relevant SearchResult objects found in data sources

    Note:
        - Limits the number of query chunks to SEARCH_CHUNKS_LIMIT
        - Times out after SEARCH_PROCESSING_TIMEOUT_SECONDS
        - Extends matched content by SEARCH_CONTEXT_EXTENSION_CHARACTERS
    """
    query_ids = _embed_user_query(query, embedder_read_queue)

    if not _wait_for_embeddings(query_ids, data_source_map):
        raise MCPError("Timeout waiting for embeddings")

    # Collect results from all data sources
    results: List[SearchResult] = []

    for query_id in query_ids:
        text_input = data_source_map.get_text_input_by_id(query_id, USER_QUERY_SOURCE)
        if text_input is None or text_input._vec is None:
            logger.warning(f"Query {query_id} is None or has no vector. text_input={text_input}")
            continue

        # Search across all non-query data sources
        data_source_results = _search_vector_in_data_source(text_input._vec, data_source_map, sources, limit + offset)
        results.extend(data_source_results)
        logger.debug(f"Found {len(data_source_results)} results")

    results = results[offset : offset + limit]

    return [result for result in sorted(results, key=lambda x: x.distance)]


def most_relevant_sources(
    query: str,
    embedder_read_queue: BulkQueue,
    data_source_map: DataSourceMap,
    sources: Optional[List[str]] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Get the most relevant sources for a query

    Args:
        query: The search query text
        embedder_read_queue: Queue to submit text chunks for embedding
        data_source_map: Data source map for searching through indexed content
        sources: List of sources to search in. If None, all sources will be searched
        limit: Maximum number of results to return

    Returns:
        List[Dict[str, Any]]: List of relevant sources with distance metrics
    """
    query_ids = _embed_user_query(query, embedder_read_queue)

    if not _wait_for_embeddings(query_ids, data_source_map):
        raise MCPError("Timeout waiting for embeddings")

    relevant_sources_grouped_by_query: Dict[str, RelevantCollection] = {}

    for query_id in query_ids:
        text_input = data_source_map.get_text_input_by_id(query_id, USER_QUERY_SOURCE)
        if text_input is None or text_input._vec is None:
            logger.warning(f"Query {query_id} is None or has no vector. text_input={text_input}")
            continue

        relevant_sources = data_source_map.get_relevant_sources(text_input._vec, limit, sources=sources)

        for relevant_source in relevant_sources:
            if relevant_source.collection not in relevant_sources_grouped_by_query:
                relevant_sources_grouped_by_query[relevant_source.collection] = relevant_source
            else:
                existing_relevant_source = relevant_sources_grouped_by_query[relevant_source.collection]
                relevant_sources_grouped_by_query[relevant_source.collection].avg_distance = (
                    existing_relevant_source.avg_distance * existing_relevant_source.count
                    + relevant_source.avg_distance * relevant_source.count
                ) / (existing_relevant_source.count + relevant_source.count)
                relevant_sources_grouped_by_query[relevant_source.collection].count += relevant_source.count
                relevant_sources_grouped_by_query[relevant_source.collection].min_distance = min(
                    existing_relevant_source.min_distance, relevant_source.min_distance
                )

    return [relevant_source.to_dict() for relevant_source in relevant_sources_grouped_by_query.values()]
