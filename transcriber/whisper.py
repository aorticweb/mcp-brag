from typing import Callable, Optional

import torch
import whisper

from server.constants import WHISPER_MODEL_SIZE
from transcriber.interface import TranscriptionProvider


class WhisperProvider(TranscriptionProvider):
    __slots__ = ["device", "model_size", "model"]
    device: torch.device
    model_size: str
    model: Optional[whisper.Whisper]

    """OpenAI Whisper transcription provider."""

    def __init__(self, model_size: str = WHISPER_MODEL_SIZE.value):
        """
        Initialize Whisper transcription provider
        
        Args:
            model_size: Size of the Whisper model to use
        """
        # Whisper only supports cpu
        # see https://github.com/pytorch/pytorch/issues/141711
        self.device = torch.device("cpu")
        self.model_size = model_size
        self.model = None

    def load_model(self):
        """
        Lazy load the Whisper model
        """
        if self.model is None:
            self.model = whisper.load_model(self.model_size, device=self.device)

    def transcribe(self, audio_path: str, chunk_callback: Optional[Callable[[int, int], None]] = None) -> str:
        """
        Transcribe audio file to text using Whisper
        
        Args:
            audio_path: Path to the audio file
            chunk_callback: Optional callback for progress updates (not used by Whisper)
        
        Returns:
            str: Transcribed text
        """
        self.load_model()
        result = self.model.transcribe(audio_path)  # type: ignore
        return result["text"]

    def get_name(self) -> str:
        """
        Get the name of this transcription provider
        
        Returns:
            str: Provider name
        """
        return "OpenAI Whisper"

    def free(self):
        """
        Free model resources
        """
        del self.model
        self.model = None