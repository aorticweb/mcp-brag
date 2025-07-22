import gc
from typing import Callable, Optional, Union

from parakeet_mlx import from_pretrained, parakeet

from server.constants import (
    PARAKEET_CHUNK_DURATION,
    PARAKEET_MODEL_PATH,
    PARAKEET_OVERLAP_DURATION,
)
from transcriber.interface import TranscriptionProvider
import mlx.core as mx

class ParakeetProvider(TranscriptionProvider):
    __slots__ = ("model_path", "chunk_duration", "overlap_duration", "model")
    """Parakeet transcription provider optimized for Metal GPU on Macs."""
    
    def __init__(
        self,
        model_path: str = PARAKEET_MODEL_PATH.value,
        chunk_duration: float = PARAKEET_CHUNK_DURATION.value,
        overlap_duration: float = PARAKEET_OVERLAP_DURATION.value,
    ):
        """
        Initialize Parakeet transcription provider
        
        Args:
            model_path: Path to the Parakeet model
            chunk_duration: Duration of audio chunks in seconds
            overlap_duration: Overlap between chunks in seconds
        """
        self.model_path = model_path
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        self.model: Optional[Union[parakeet.ParakeetTDT, parakeet.ParakeetCTC]] = None

    def load_model(self):
        """
        Lazy load the Parakeet model
        """
        if self.model is None:
            self.model = from_pretrained(self.model_path)

    def transcribe(self, audio_path: str, chunk_callback: Optional[Callable[[int, int], None]] = None) -> str:
        """
        Transcribe audio file to text using Parakeet
        
        Args:
            audio_path: Path to the audio file
            chunk_callback: Optional callback for progress updates
        
        Returns:
            str: Transcribed text
        """
        self.load_model()
        result = self.model.transcribe( # type: ignore
            audio_path,
            chunk_duration=self.chunk_duration,
            overlap_duration=self.overlap_duration,
            chunk_callback=chunk_callback,
        )
        return result.text

    def get_name(self) -> str:
        """
        Get the name of this transcription provider
        
        Returns:
            str: Provider name with model path
        """
        return f"Parakeet [{self.model_path}]"

    def free(self):
        """
        Free model resources and clear cache
        """
        mx.clear_cache()
        del self.model
        self.model = None