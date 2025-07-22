import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

import yt_dlp

from common import log
from server.constants import TEMP_AUDIO_DIR
from server.workers.ingestion_state_manager import (
    IngestionPhase,
    SourceIngestionProgressManager,
)

logger = log.get_logger(__name__)


@dataclass
class YoutubeDownloadOutput:
    file_id: str
    url: str
    audio_file_path: Path
    audio_folder_path: Path  # to be deleted when processing is done
    title: str
    video_id: str
    duration: int
    uploader: str


def get_progress_hook(url: str, progress_manager: SourceIngestionProgressManager) -> Callable[[Dict], None]:
    def progress_hook(d: dict):
        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes")
            if total_bytes and downloaded:
                progress_manager.set_phase_total(url, IngestionPhase.DOWNLOADING, total_bytes)
                progress_manager.set_phase_progress(url, IngestionPhase.DOWNLOADING, downloaded)

    return progress_hook


class YouTubeDownloader:
    """Main YouTube transcription class."""

    def __init__(self, temp_dir: str = TEMP_AUDIO_DIR.value):
        # TODO:
        # validate temp_dir is a valid path
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True, mode=0o755)

    def download_audio(
        self, url: str, progress_manager: Optional[SourceIngestionProgressManager] = None
    ) -> YoutubeDownloadOutput:
        """Download audio from YouTube video."""
        _id = str(uuid.uuid4())[:12]
        folder = self.temp_dir / _id
        folder.mkdir(parents=True, exist_ok=True, mode=0o755)
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": str(folder / f"{_id}.%(ext)s"),
        }
        if progress_manager:
            ydl_opts["progress_hooks"] = [get_progress_hook(url, progress_manager)]  # type: ignore

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_title = info_dict.get("title", "unknown")
            video_id = info_dict.get("id", "unknown")

            audio_file = None
            logger.debug(f"Searching for audio file in {folder}")
            for file in folder.glob("*"):
                if file.is_file():
                    # Check that the file name matches the _id value
                    if _id not in file.name:
                        logger.debug(f"Skipping file {file} because it does not match the _id value {_id}")
                        continue
                    audio_file = file
                    break

            if not audio_file:
                if progress_manager:
                    progress_manager.mark_as_failed(url)
                raise Exception("Failed to find downloaded audio file")

            return YoutubeDownloadOutput(
                file_id=_id,
                url=url,
                audio_file_path=audio_file,
                audio_folder_path=folder,
                title=video_title,
                video_id=video_id,
                duration=info_dict.get("duration", 0),
                uploader=info_dict.get("uploader", "unknown"),
            )
