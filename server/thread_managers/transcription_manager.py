import shutil
import time
from pathlib import Path

from common.log import get_logger
from embedder.read_write.bulk_queue import BulkQueue
from embedder.text import TextInput
from server.constants import AUDIO_TRANSCRIPTION_DIR, AUDIO_TRANSCRIPTION_IDLE_TIMEOUT
from server.thread_managers.interface import SelfTerminatingThreadManager
from server.workers.embedding import (
    TranscriptionTask,
    generate_embeddings_for_audio_transcription,
)
from server.workers.ingestion_state_manager import (
    IngestionPhase,
    SourceIngestionProgressManager,
)
from transcriber import TranscriptionProvider

logger = get_logger(__name__)


def chunk_callback_func(source: str, ingestion_state_manager: SourceIngestionProgressManager):
    def callback(chunk_index: int, total_chunks: int):
        ingestion_state_manager.set_phase_progress(source, IngestionPhase.TRANSCRIPTION, chunk_index)
        ingestion_state_manager.set_phase_total(source, IngestionPhase.TRANSCRIPTION, total_chunks)

    return callback


class TranscriptionThreadManager(SelfTerminatingThreadManager):
    def __init__(
        self,
        transcription_queue: BulkQueue[TranscriptionTask],
        embedder_read_queue: BulkQueue[TextInput],
        transcription_provider: TranscriptionProvider,
        ingestion_state_manager: SourceIngestionProgressManager,
    ):
        """Initialize the transcription thread manager.

        Args:
            transcription_queue: Queue for receiving audio file paths to transcribe
            embedder_read_queue: Queue for sending chunked transcriptions to embedder
            transcription_provider: Provider for transcribing audio files
        """
        self._transcription_queue = transcription_queue
        self._embedder_read_queue = embedder_read_queue
        self._provider = transcription_provider
        self._ingestion_state_manager = ingestion_state_manager
        super().__init__(activity_timeout=AUDIO_TRANSCRIPTION_IDLE_TIMEOUT.value)

    def run(self):
        """Run the transcription loop until stopped or idle timeout."""
        logger.info("Starting transcription thread")
        progress_manager = self._ingestion_state_manager
        while not self._should_stop:
            task = self._transcription_queue.get_one()  # Process up to 5 at once

            if task is None:
                if self.should_terminate_due_to_idle():
                    break
                # Sleep briefly to avoid busy waiting
                time.sleep(0.3)
                continue
            self.mark_as_active()

            # Set progress state
            progress_manager.add_phase(task.source, IngestionPhase.TRANSCRIPTION, total=1)
            chunk_callback = chunk_callback_func(task.source, progress_manager)

            # Transcribe
            transcript = self._provider.transcribe(task.audio_path, chunk_callback)
            transcript_path = str(Path(AUDIO_TRANSCRIPTION_DIR.value) / f"{task.id}.txt")
            Path(transcript_path).parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            with open(transcript_path, "w") as f:
                f.write(transcript)

            logger.debug(f"Deleting audio folder at {task.audio_folder_path}")
            if task.delete_audio_folder:
                shutil.rmtree(task.audio_folder_path)

            # Update progress state
            progress_manager.increment_phase_progress(task.source, IngestionPhase.TRANSCRIPTION, 1)

            # Generate embeddings
            generate_embeddings_for_audio_transcription(
                transcript_path,
                task.source,
                task.source_type,
                self._embedder_read_queue,
                self._ingestion_state_manager,
                {"transcription_path": transcript_path},
            )

        self._provider.free()
        logger.info("Transcription thread terminated")

    def name(self) -> str:
        return "Transcription Thread Manager"
