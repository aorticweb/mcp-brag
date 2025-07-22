import json
from datetime import timedelta
from typing import Any, Dict

from common.config.constant import Constant
from embedder.constants import (
    BULK_QUEUE_FULL_RETRY_COUNT,
    BULK_QUEUE_FULL_SLEEP_TIME,
    EMBEDDING_SIZE,
    SQLITE_DB_LOCATION,
    VECTORIZER_MODEL_PATH,
)
from server.constants import (
    AUDIO_TRANSCRIPTION_DIR,
    AUDIO_TRANSCRIPTION_IDLE_TIMEOUT,
    CHUNK_CHARACTER_LIMIT,
    DOWNLOAD_THREAD_IDLE_TIMEOUT,
    EMBEDDER_IDLE_TIMEOUT,
    INGESTION_PROCESS_MAX_FILE_PATHS,
    INSTRUCTIONS,
    PARAKEET_CHUNK_DURATION,
    PARAKEET_MODEL_PATH,
    PARAKEET_OVERLAP_DURATION,
    SEARCH_CHUNK_CHARACTER_LIMIT,
    SEARCH_CHUNKS_LIMIT,
    SEARCH_CONTEXT_EXTENSION_CHARACTERS,
    SEARCH_PROCESSING_TIMEOUT_SECONDS,
    SEARCH_RESULT_LIMIT,
    TEMP_AUDIO_DIR,
    WHISPER_MODEL_SIZE,
)
from server.error import MCPError

editable_name_to_config_map: Dict[str, Constant[Any]] = {
    # TODO:
    # "VECTORIZER_MODEL_PATH": VECTORIZER_MODEL_PATH,
    "INGESTION_PROCESS_MAX_FILE_PATHS": INGESTION_PROCESS_MAX_FILE_PATHS,
    "CHUNK_CHARACTER_LIMIT": CHUNK_CHARACTER_LIMIT,
    "SEARCH_CHUNK_CHARACTER_LIMIT": SEARCH_CHUNK_CHARACTER_LIMIT,
    "SEARCH_CHUNKS_LIMIT": SEARCH_CHUNKS_LIMIT,
    "SEARCH_PROCESSING_TIMEOUT_SECONDS": SEARCH_PROCESSING_TIMEOUT_SECONDS,
    "SEARCH_CONTEXT_EXTENSION_CHARACTERS": SEARCH_CONTEXT_EXTENSION_CHARACTERS,
    "SEARCH_RESULT_LIMIT": SEARCH_RESULT_LIMIT,
}

frozen_config_map: Dict[str, Constant[Any]] = {
    "AUDIO_TRANSCRIPTION_DIR": AUDIO_TRANSCRIPTION_DIR,
    "AUDIO_TRANSCRIPTION_IDLE_TIMEOUT": AUDIO_TRANSCRIPTION_IDLE_TIMEOUT,
    "DOWNLOAD_THREAD_IDLE_TIMEOUT": DOWNLOAD_THREAD_IDLE_TIMEOUT,
    "EMBEDDER_IDLE_TIMEOUT": EMBEDDER_IDLE_TIMEOUT,
    "VECTORIZER_MODEL_PATH": VECTORIZER_MODEL_PATH,
    "EMBEDDING_SIZE": EMBEDDING_SIZE,
    "SQLITE_DB_LOCATION": SQLITE_DB_LOCATION,
    "BULK_QUEUE_FULL_SLEEP_TIME": BULK_QUEUE_FULL_SLEEP_TIME,
    "BULK_QUEUE_FULL_RETRY_COUNT": BULK_QUEUE_FULL_RETRY_COUNT,
    "INSTRUCTIONS": INSTRUCTIONS,
    "TEMP_AUDIO_DIR": TEMP_AUDIO_DIR,
    "WHISPER_MODEL_SIZE": WHISPER_MODEL_SIZE,
    "PARAKEET_MODEL_PATH": PARAKEET_MODEL_PATH,
    "PARAKEET_CHUNK_DURATION": PARAKEET_CHUNK_DURATION,
    "PARAKEET_OVERLAP_DURATION": PARAKEET_OVERLAP_DURATION,
}


def validate_config_type(constant: Constant[Any], value: Any) -> Any:
    error = MCPError(
        f"Invalid config value or type: for constant of type [{constant.default_type}] and value [{value}]"
    )
    try:
        # Direct type match - return as is
        if constant.default_type == type(value):
            return value

        # Type conversions
        if constant.default_type == str:
            return str(value)

        elif constant.default_type == int:
            if isinstance(value, str):
                return int(value)
            elif isinstance(value, float):
                return int(value)
            elif isinstance(value, int):
                return value
            return int(value)

        elif constant.default_type == float:
            if isinstance(value, str):
                return float(value)
            elif isinstance(value, (int, float)):
                return float(value)
            return float(value)

        elif constant.default_type == bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            if isinstance(value, (int, float)):
                return bool(value)
            return bool(value)

        elif constant.default_type == timedelta:
            if isinstance(value, timedelta):
                return value
            if isinstance(value, (int, float)):
                return timedelta(seconds=value)
            if isinstance(value, str):
                return timedelta(seconds=float(value))
            return timedelta(seconds=float(value))

        elif constant.default_type == list:
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                if not value.strip():
                    return []
                # Handle comma-separated values
                return [item.strip() for item in value.split(",")]
            return list(value)

        elif constant.default_type == dict:
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                return json.loads(value)
            return dict(value)
    except Exception:
        raise error

    raise error


def format_config(value: Any, is_frozen: bool = False) -> Dict[str, Any]:
    return {"value": value, "type": type(value).__name__, "frozen": is_frozen}


def edit_config(name: str, value: Any) -> Dict[str, Any]:
    if name.upper() not in editable_name_to_config_map:
        raise MCPError(f"Invalid config name: {name}")
    constant = editable_name_to_config_map[name.upper()]
    validated_value = validate_config_type(constant, value)
    constant.set(validated_value)
    return {name.upper(): format_config(validated_value)}


def all_configs() -> Dict[str, Any]:
    data = {}
    for name, constant in editable_name_to_config_map.items():
        data[name.upper()] = format_config(constant.value)
    for name, constant in frozen_config_map.items():
        data[name.upper()] = format_config(constant.value, is_frozen=True)
    return data
