from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterator

from server.constants import CHUNK_CHARACTER_LIMIT


@dataclass
class TextChunk:
    """Represents a chunk of text with its position information.

    Attributes:
        start_index: The starting character index of the chunk in the original text
        end_index: The ending character index of the chunk in the original text
        text: The actual text content of the chunk
    """

    start_index: int
    end_index: int
    text: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert the TextChunk to a dictionary representation.

        Returns:
            Dict containing the chunk's start_index, end_index, and text
        """
        return {
            "start_index": self.start_index,
            "end_index": self.end_index,
            "text": self.text,
        }


class SourceType(str, Enum):
    """Enumeration of possible source types for text inputs."""

    LOCAL_TEXT_FILE = "LOCAL_TEXT_FILE"
    LOCAL_PDF_FILE = "LOCAL_PDF_FILE"
    LOCAL_DOCX_FILE = "LOCAL_DOCX_FILE"
    LOCAL_DOC_FILE = "LOCAL_DOC_FILE"
    LOCAL_PPTX_FILE = "LOCAL_PPTX_FILE"
    LOCAL_PPT_FILE = "LOCAL_PPT_FILE"
    LOCAL_HTML_FILE = "LOCAL_HTML_FILE"
    YOUTUBE_TRANSCRIPTION = "YOUTUBE_TRANSCRIPTION"
    LOCAL_AUDIO_FILE = "LOCAL_AUDIO_FILE"
    USER_QUERY = "user_query"


class Reader(ABC):
    @abstractmethod
    def __init__(self, file_path: str, chunk_size_max: int = CHUNK_CHARACTER_LIMIT.value):
        pass

    @abstractmethod
    def read(self) -> str:
        pass

    @abstractmethod
    def read_iter(self) -> Iterator[TextChunk]:
        pass

    @abstractmethod
    def source_type(self) -> SourceType:
        pass
