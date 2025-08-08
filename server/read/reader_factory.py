# from server.read.epub_reader import EpubReader
# from server.read.fb2_reader import Fb2Reader
# from server.read.rtf_reader import RtfReader
# from server.read.odt_reader import OdtReader
# from server.read.odp_reader import OdpReader
# from server.read.markdown_reader import MarkdownReader
# from server.read.pages_reader import PagesReader
# from server.read.key_reader import KeynoteReader
# from server.read.abw_reader import AbwReader
# from server.read.tex_reader import TexReader
# from server.read.vtt_reader import VttReader
# from server.read.srt_reader import SrtReader
# from server.read.msg_reader import MsgReader
# from server.read.eml_reader import EmlReader
import os
from typing import Dict, Type

from common.log import get_logger
from server.constants import CHUNK_CHARACTER_LIMIT
from server.read.docx_reader import DocxReader
from server.read.html_reader import HTMLReader
from server.read.pdf_reader import PDFReader
from server.read.pptx_reader import PptxReader
from server.read.reader import Reader
from server.read.text_reader import TextReader

logger = get_logger(__name__)


class ReaderFactory:
    """Factory class to create appropriate Reader instances based on file extension."""

    # Mapping of file extensions to reader classes
    EXTENSION_READERS: Dict[str, Type[Reader]] = {
        # PDF
        ".pdf": PDFReader,
        # Microsoft Office
        ".docx": DocxReader,
        # ".doc": DocReader,
        ".pptx": PptxReader,
        # ".ppt": PptReader,
        ".ppsx": PptxReader,  # PowerPoint Show
        ".pptm": PptxReader,  # PowerPoint Macro-Enabled
        # ".pps": PptReader,  # PowerPoint Show (legacy)
        # # OpenDocument
        # '.odt': OdtReader,
        # '.odp': OdpReader,
        # # E-books
        # '.epub': EpubReader,
        # '.fb2': Fb2Reader,
        # Text formats
        ".txt": TextReader,
        # '.rtf': RtfReader,
        ".html": HTMLReader,
        ".htm": HTMLReader,
        # '.md': MarkdownReader,
        # '.markdown': MarkdownReader,
        # '.tex': TexReader,
        # # Apple iWork
        # '.pages': PagesReader,
        # '.key': KeynoteReader,
        # # Other formats
        # '.abw': AbwReader,
        # # Subtitles and captions
        # '.vtt': VttReader,
        # '.srt': SrtReader,
        # # Email formats
        # '.msg': MsgReader,
        # '.eml': EmlReader,
    }

    @classmethod
    def create_reader(cls, file_path: str, chunk_size_max: int = CHUNK_CHARACTER_LIMIT.value) -> Reader:
        """
        Create an appropriate Reader instance based on file extension or MIME type.

        Args:
            file_path: Path to the file
            chunk_size_max: Maximum size for text chunks

        Returns:
            Reader instance appropriate for the file type

        Raises:
            ValueError: If no suitable reader is found for the file type
        """

        # Get file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        # Find appropriate reader
        if ext in cls.EXTENSION_READERS:
            reader_class = cls.EXTENSION_READERS[ext]
            return reader_class(file_path, chunk_size_max=chunk_size_max)

        logger.warning(f"No reader found for file {file_path} defaulting to text reader")
        # Default to text reader for unknown extensions
        return TextReader(file_path, chunk_size_max=chunk_size_max)

    @classmethod
    def get_supported_extensions(cls) -> list:
        """Get list of all supported file extensions."""
        return list(cls.EXTENSION_READERS.keys())

    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """
        Check if a file type is supported.

        Args:
            file_path: Path to the file

        Returns:
            True if the file type is supported, False otherwise
        """

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        return ext in cls.EXTENSION_READERS
