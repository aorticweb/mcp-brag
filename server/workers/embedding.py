from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from common.log import get_logger
from embedder.read_write.bulk_queue import BulkQueue
from embedder.text import TextInput
from server.error import MCPError
from server.read import ReaderFactory
from server.read.reader import SourceType
from server.read.text_reader import TextReader
from server.workers.ingestion_state_manager import (
    IngestionPhase,
    SourceIngestionProgressManager,
)

logger = get_logger(__name__)


@dataclass
class TranscriptionTask:
    """Represents a transcription task with metadata."""

    id: str
    audio_path: str
    audio_folder_path: str
    source: str
    source_type: SourceType
    task_id: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    delete_audio_folder: bool = True


AUDIO_FILE_EXTENSIONS = [".mp3", ".wav", ".m4a", ".flac", ".ogg"]


def handle_audio_file(file_path: str, transcription_queue: BulkQueue, progress_manager: SourceIngestionProgressManager):
    """Handle audio file for embedding.

    Args:
        file_path: Path to the audio file
        embedder_read_queue: Queue to submit text chunks for embedding
        progress_manager: Progress manager for tracking progress
    """
    path = Path(file_path)
    if not path.exists():
        raise MCPError(f"File {file_path} does not exist")

    if path.suffix.lower() not in AUDIO_FILE_EXTENSIONS:
        raise MCPError(f"File {file_path} with suffix {path.suffix} is not an audio file")

    task = TranscriptionTask(
        id=str(uuid4()),
        audio_path=str(path),
        audio_folder_path=str(path.parent),
        source=str(path),
        source_type=SourceType.LOCAL_AUDIO_FILE,
        task_id=str(uuid4()),
        created_at=datetime.now(),
        metadata={},
        delete_audio_folder=False,
    )
    progress_manager.add_phase(file_path, IngestionPhase.TRANSCRIPTION)
    progress_manager.add_phase(file_path, IngestionPhase.EMBEDDING)
    progress_manager.add_phase(file_path, IngestionPhase.STORING)
    transcription_queue.put_many([task])


def generate_embeddings_for_file(
    file_path: str,
    embedder_read_queue: BulkQueue,
    transcription_queue: BulkQueue,
    progress_manager: SourceIngestionProgressManager,
) -> Optional[int]:
    """Generate embeddings for text content from a file.

    Reads a file line by line, splits content into chunks, and submits them
    to the embedder queue for processing.

    Args:
        file_path: Path to the file to process
        embedder_read_queue: Queue to submit text chunks for embedding

    Returns:
        Total number of chunks generated

    Raises:
        MCPError: If the specified file does not exist
    """
    if any([file_path.endswith(ext) for ext in AUDIO_FILE_EXTENSIONS]):
        handle_audio_file(file_path, transcription_queue, progress_manager)
        return None

    progress_manager.add_phase(file_path, IngestionPhase.EMBEDDING)
    progress_manager.add_phase(file_path, IngestionPhase.STORING)

    path = Path(file_path)
    if not path.exists():
        progress_manager.mark_as_failed(file_path)
        raise MCPError(f"File {file_path} does not exist")

    text_inputs = []
    total_chunks = 0

    reader = ReaderFactory.create_reader(file_path)
    for chunk in reader.read_iter():
        text_inputs.append(
            TextInput(
                chunk.text,
                {
                    "id": str(uuid4()),
                    "source": file_path,
                    "source_type": reader.source_type(),
                    **chunk.to_dict(),
                },
                source_id=file_path,
            )
        )
        total_chunks += 1

    if not text_inputs:
        progress_manager.mark_as_completed(file_path)
        return 0

    progress_manager.set_phase_total(file_path, IngestionPhase.EMBEDDING, total_chunks)
    progress_manager.set_phase_total(file_path, IngestionPhase.STORING, total_chunks)
    embedder_read_queue.put_many(text_inputs)

    logger.debug(f"Generated {total_chunks} chunks")
    return total_chunks


def generate_embeddings_for_audio_transcription(
    file_path: str,
    source: str,
    source_type: SourceType,
    embedder_read_queue: BulkQueue,
    progress_manager: SourceIngestionProgressManager,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """Generate embeddings for text content from a file.

    Reads a file line by line, splits content into chunks, and submits them
    to the embedder queue for processing.

    Args:
        file_path: Path to the file to process
        source: Source of the audio transcription
        source_type: Type of the source
        embedder_read_queue: Queue to submit text chunks for embedding
        extra_metadata: Extra metadata to add to the text input

    Returns:
        Total number of chunks generated

    Raises:
        MCPError: If the specified file does not exist
    """
    path = Path(file_path)
    if not path.exists():
        raise MCPError(f"File {file_path} does not exist")

    progress_manager.add_phase(source, IngestionPhase.EMBEDDING)
    if extra_metadata is None:
        extra_metadata = {}

    text_inputs = []
    total_chunks = 0

    reader = TextReader(file_path)
    for chunk in reader.read_iter():
        text_inputs.append(
            TextInput(
                chunk.text,
                {
                    "id": str(uuid4()),
                    "source": source,
                    "source_type": source_type,
                    **extra_metadata,
                    **chunk.to_dict(),
                },
                source_id=source,
            )
        )
        total_chunks += 1

    if not text_inputs:
        return 0

    progress_manager.set_phase_total(source, IngestionPhase.EMBEDDING, total_chunks)
    progress_manager.set_phase_total(source, IngestionPhase.STORING, total_chunks)

    embedder_read_queue.put_many(text_inputs)

    logger.debug(f"Generated {total_chunks} chunks")
    return total_chunks
