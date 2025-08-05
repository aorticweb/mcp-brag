"""Constants used throughout the server module."""

from datetime import timedelta
from pathlib import Path

from common.config.constant import Constant
from embedder.constants import app_dir_path

# Search configuration
SEARCH_CHUNK_CHARACTER_LIMIT = Constant(1000, env_var="SEARCH_CHUNK_CHARACTER_LIMIT")
SEARCH_CHUNKS_LIMIT = Constant(30, env_var="SEARCH_CHUNKS_LIMIT")
SEARCH_PROCESSING_TIMEOUT_SECONDS = Constant(10, env_var="SEARCH_PROCESSING_TIMEOUT_SECONDS")
SEARCH_CONTEXT_EXTENSION_CHARACTERS = Constant(1000, env_var="SEARCH_CONTEXT_EXTENSION_CHARACTERS")
SEARCH_RESULT_LIMIT = Constant(5, "SEARCH_RESULT_LIMIT")
DEEP_SEARCH_RESULT_LIMIT = Constant(30, "DEEP_SEARCH_RESULT_LIMIT")
MAX_SOURCES_IN_DEEP_SEARCH = Constant(3, "MAX_SOURCES_IN_DEEP_SEARCH")

# MCP configuration
INSTRUCTIONS = Constant(
    """
This MCP server is called "Brag".
The main tools are `search`, `most_relevant_files` and `deep_search`.

`search`: It allows you to search for information in data sources to better answer questions that the user prompted
using factual information and avoid hallucinations.

`most_relevant_files`: It allows you to find the most relevant files for a query. This tool should be used to find relevant files and then use the deep_search tool to get more enhanced results.

`deep_search`: It allows you to search for relevant content across the given sources based on a query and get significantly more relevant results. Before using this tool, you should use the most_relevant_files tool to find the most relevant sources.

There are two ways to use the tools:
Workflow 1:
User ask a question that requires light factual information. => use search tool

Workflow 2:
User ask a question that requires deep factual information. => use most_relevant_files tool to find the most relevant files and then use the deep_search tool to get more enhanced results.

You should use these tool to get factual information prior to answering the user prompt, if the search results are relevant to the user prompt
and the distance is less than 0.9. the search will return multiple results ranked by distance, the lower the distance, the more relevant the result is.
Use the best result and if the result sets has a lot of variance, use your best judgement to ignore the results that are not relevant to the user prompt.

When using search result from this tool, you should site the search results you used to answer the user prompt.

If the user mentioned "Brag" in the prompt, you HAVE to use some of the tools to answer the user prompt.
""",
    env_var="MCP_INSTRUCTIONS",
)

# Audio transcription configuration
TEMP_AUDIO_DIR = Constant(str(app_dir_path() / "temp_audio"), env_var="TEMP_AUDIO_DIR")
AUDIO_TRANSCRIPTION_DIR = Constant(str(app_dir_path() / "audio_transcriptions"), env_var="AUDIO_TRANSCRIPTION_DIR")
WHISPER_MODEL_SIZE = Constant("base", env_var="WHISPER_MODEL_SIZE")
PARAKEET_MODEL_PATH = Constant("mlx-community/parakeet-tdt-0.6b-v2", env_var="PARAKEET_MODEL_PATH")
PARAKEET_CHUNK_DURATION = Constant(300.0, env_var="PARAKEET_CHUNK_DURATION")
PARAKEET_OVERLAP_DURATION = Constant(15.0, env_var="PARAKEET_OVERLAP_DURATION")

# Thread managers configuration
DOWNLOAD_THREAD_IDLE_TIMEOUT = Constant(timedelta(seconds=300), env_var="DOWNLOAD_THREAD_IDLE_TIMEOUT")
EMBEDDER_IDLE_TIMEOUT = Constant(timedelta(seconds=10), "EMBEDDER_IDLE_TIMEOUT")
AUDIO_TRANSCRIPTION_IDLE_TIMEOUT = Constant(timedelta(seconds=10), env_var="AUDIO_TRANSCRIPTION_IDLE_TIMEOUT")

# Text processing configuration
CHUNK_CHARACTER_LIMIT = Constant(1500, env_var="CHUNK_CHARACTER_LIMIT")

# Embedder manager configuration

# Data ingestion configuration
INGESTION_PROCESS_MAX_FILE_PATHS = Constant(100, env_var="INGESTION_PROCESS_MAX_FILE_PATHS")
