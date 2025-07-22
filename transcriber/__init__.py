from transcriber.interface import TranscriptionProvider  # noqa: F401
from transcriber.parakeet import ParakeetProvider  # noqa: F401
from transcriber.whisper import WhisperProvider  # noqa: F401

from enum import Enum

class TranscriberTypes(str, Enum):
    PARAKEET = "parakeet"
    WHISPER = "whisper"


def get_transcription_provider(
    model_type: TranscriberTypes
) -> TranscriptionProvider:
    """
    Get a transcription provider based on the specified type
    
    Args:
        model_type: Type of transcription model to use
    
    Returns:
        TranscriptionProvider: Instance of the requested provider
    """
    if model_type == TranscriberTypes.PARAKEET:
        return ParakeetProvider()
    elif model_type == TranscriberTypes.WHISPER:
        return WhisperProvider()
    raise ValueError(f"Invalid model type: {model_type}")
