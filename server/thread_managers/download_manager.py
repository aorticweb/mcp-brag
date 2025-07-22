import time
from datetime import datetime
from urllib.parse import urlparse
from uuid import uuid4

from common.log import get_logger
from embedder.read_write.bulk_queue import BulkQueue
from server.constants import DOWNLOAD_THREAD_IDLE_TIMEOUT
from server.read.reader import SourceType
from server.thread_managers.interface import SelfTerminatingThreadManager
from server.thread_managers.transcription_manager import TranscriptionTask
from server.workers.download import YouTubeDownloader
from server.workers.ingestion_state_manager import (
    IngestionPhase,
    SourceIngestionProgressManager,
)

logger = get_logger(__name__)


class DownloadManager(SelfTerminatingThreadManager):
    def __init__(
        self,
        download_queue: BulkQueue[str],
        transcription_queue: BulkQueue[TranscriptionTask],
        ingestion_state_manager: SourceIngestionProgressManager,
    ):
        """Initialize the YouTube download manager.

        Args:
            bulk_queue: Queue for receiving YouTube URLs to process
            transcription_queue: Queue for sending audio file paths to transcription manager
        """
        self._download_queue = download_queue
        self._transcription_queue = transcription_queue
        self._ingestion_state_manager = ingestion_state_manager
        super().__init__(activity_timeout=DOWNLOAD_THREAD_IDLE_TIMEOUT.value)

    def _is_valid_youtube_url(self, url: str) -> bool:
        """Check if the URL is a valid YouTube URL.

        Args:
            url: URL string to validate

        Returns:
            True if valid YouTube URL, False otherwise
        """
        # extra type safety since value comes from the queue
        if not isinstance(url, str):
            return False

        try:
            parsed = urlparse(url)
            if parsed.scheme not in ["http", "https"]:
                return False

            # Check for YouTube domains
            if parsed.netloc in ["youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"]:
                return True

            # Check for YouTube in any part of the domain
            if "youtube" in parsed.netloc:
                return True

            return False
        except Exception:
            return False

    def _process_url(self, url: str):
        """Process a single YouTube URL.

        Args:
            url: YouTube URL to download
        """
        if not self._is_valid_youtube_url(url):
            logger.error(f"Invalid YouTube URL ignored: {url}")
            return

        progress_manager = self._ingestion_state_manager
        progress_manager.add_phase(url, IngestionPhase.DOWNLOADING, total=1)
        try:
            logger.debug(f"Downloading YouTube URL: {url}")
            download_output = YouTubeDownloader().download_audio(url, progress_manager)
        except Exception as e:
            progress_manager.mark_as_failed(url)
            logger.error(f"Error processing YouTube URL {url}: {e}")
            return

        task = TranscriptionTask(
            id=download_output.file_id,
            audio_path=str(download_output.audio_file_path),
            audio_folder_path=str(download_output.audio_folder_path),
            source=url,
            source_type=SourceType.YOUTUBE_TRANSCRIPTION,
            task_id=str(uuid4()),
            created_at=datetime.now(),
            metadata={
                "title": download_output.title,
                "video_id": download_output.video_id,
                "duration": download_output.duration,
                "uploader": download_output.uploader,
                "temp_folder": str(download_output.audio_folder_path),
            },
        )
        self._transcription_queue.put_many([task])
        logger.debug(f"Successfully queued audio from {url} for transcription")

    def run(self):
        """Run the consumer loop until stopped or idle timeout."""
        logger.info("Starting YouTube download consumer thread")

        while not self._should_stop:
            # TODO:
            # run a few downloads in parallel
            url = self._download_queue.get_one()
            if url is None:
                if self.should_terminate_due_to_idle():
                    break
                time.sleep(0.3)
                continue

            self.mark_as_active()
            self._process_url(url)

        logger.info("YouTube download consumer thread terminated")

    def name(self) -> str:
        return "Download Thread Manager"
