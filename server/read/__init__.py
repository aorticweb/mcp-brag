from .docx_reader import DocxReader
from .html_reader import HTMLReader
from .pdf_reader import PDFReader
from .pptx_reader import PptxReader

# Import all readers for easy access
from .reader import Reader, SourceType
from .reader_factory import ReaderFactory
from .text_reader import TextReader

# Commented out non-existent readers
# from .doc_reader import DocReader
# from .ppt_reader import PptReader
# from .epub_reader import EpubReader
# from .fb2_reader import Fb2Reader
# from .rtf_reader import RtfReader
# from .odt_reader import OdtReader
# from .odp_reader import OdpReader
# from .markdown_reader import MarkdownReader
# from .pages_reader import PagesReader
# from .key_reader import KeynoteReader
# from .abw_reader import AbwReader
# from .tex_reader import TexReader
# from .vtt_reader import VttReader
# from .srt_reader import SrtReader
# from .msg_reader import MsgReader
# from .eml_reader import EmlReader

__all__ = [
    "Reader",
    "TextReader",
    "PDFReader",
    "DocxReader",
    "DocReader",
    "PptxReader",
    "HTMLReader",
    "ReaderFactory",
    "SourceType",
]
