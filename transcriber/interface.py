from abc import ABC, abstractmethod
from typing import Callable, Optional

class TranscriptionProvider(ABC):
    """Abstract base class for transcription providers."""

    @abstractmethod
    def transcribe(self, audio_path: str, chunk_callback: Optional[Callable[[int, int], None]] = None) -> str:
        """
        Transcribe audio file and return text
        
        Args:
            audio_path: Path to the audio file to transcribe
            chunk_callback: Optional callback for progress updates (current_chunk, total_chunks)
        
        Returns:
            str: Transcribed text from the audio
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Return provider name
        
        Returns:
            str: Name of the transcription provider
        """
        pass

    @abstractmethod
    def free(self):
        """
        Free resources used by the provider
        """
        pass