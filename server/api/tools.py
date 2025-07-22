from typing import Any, Dict, List

from fastmcp.tools.tool import Tool

from server.api.internal import _deep_search, _most_relevant_files, _search_files


def search_files(query: str, offset: int = 0) -> Dict[str, Any]:
    """Search for relevant content across all processed files based on a query.
    The tool can be used iteratively to get more results by paginating the function call using the offset parameter.
    The response data will have the following format
    ```
        {
            "status": "success",
            "query": query,
            "results_count": len(formatted_results),
            "results": [
                {
                    "text": "The text of the result that you should use to find the information to answer the query",
                    "source": "The source of the result",
                }
            ]
        }
    ```
    use response.results[0..n]["text"] to answer the user's question
    Args:
        query (str): The search query
        offset (int): Number of results to skip, when iterating over results (default: 0)

    Returns:
        Dict[str, Any]: The search results with detailed information
    """
    return _search_files(query, offset)


def most_relevant_files(query: str) -> Dict[str, Any]:
    """Get the most relevant files for a query.

    This tool should be used to find relevant files and then use the deep_search tool to get more enhanced results.
    The response data will have the following format
    ```
        {
            "status": "success",
            "most_relevant_sources": [
                {
                    "source": "The name of the source",
                    "min_distance": "The minimum distance of the source",
                    "avg_distance": "The average distance of the source",
                    "count": "The number of results for the source"
                }
            ]
        }
    ```

    The name of the source should then be passed to the deep_search tool sources argument.
    Args:
        query (str): The search query

    Returns:
        Dict[str, Any]: The most relevant files for the query
    """
    return _most_relevant_files(query)


def deep_search(query: str, sources: List[str]) -> Dict[str, Any]:
    """Search for relevant content across the given sources based on a query and get significantly more relevant results.

    Before using this tool, you should use the most_relevant_files tool to find the most relevant sources.
    The response data will have the following format
    ```
        {
            "status": "success",
            "query": query,
            "results_count": len(formatted_results),
            "results": [
                {
                    "text": "The text of the result that you should use to find the information to answer the query",
                    "source": "The source of the result",
                }
            ]
        }
    ```
    use response.results[0..n]["text"] to answer the user's question
    Args:
        query (str): The search query
        sources (List[str]): The list of sources to search in

    Returns:
        Dict[str, Any]: The search results with detailed information
    """
    return _deep_search(query, sources)


TOOLS = [
    Tool.from_function(
        search_files,
        name="search",
        description="Search for relevant content across all processed files based on a query. The tool can be used iteratively to get more results by paginating the function call using the offset parameter. The response data will have the following format",
    ),
    Tool.from_function(
        most_relevant_files,
        name="most_relevant_files",
        description="Get the most relevant files for a query. This tool should be used to find relevant files and then use the deep_search tool to get more enhanced results.",
    ),
    Tool.from_function(
        deep_search,
        name="deep_search",
        description="Search for relevant content across the given sources based on a query and get significantly more relevant results. Before using this tool, you should use the most_relevant_files tool to find the most relevant sources.",
    ),
]
