from typing import Iterator

import PyPDF2

from server.constants import CHUNK_CHARACTER_LIMIT
from server.read.reader import Reader, SourceType, TextChunk
from server.read.text_reader import _split_text_chunk


class PDFReader(Reader):
    file_path: str
    chunk_size_max: int

    def __init__(self, file_path: str, chunk_size_max: int = CHUNK_CHARACTER_LIMIT.value):
        self.file_path = file_path
        self.chunk_size_max = chunk_size_max

    def source_type(self) -> SourceType:
        return SourceType.LOCAL_PDF_FILE

    def read(self) -> str:
        """
        Read the PDF file and return all text content as a single string.

        Returns:
            str: The extracted text content from all pages
        """
        pdf_text = ""
        with open(self.file_path, "rb") as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                pdf_text += page.extract_text() + "\n"
        return pdf_text

    def read_iter(self) -> Iterator[TextChunk]:
        """
        Read the PDF file and yield TextChunk objects for each page's text content.

        Each page becomes a TextChunk with start_index and end_index representing
        the character positions in the concatenated text from all pages.

        Yields:
            TextChunk: Chunk containing page text and its character indices
        """
        char_index = 0

        with open(self.file_path, "rb") as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()

                # Add newline to match the behavior of the read() method
                if page_num < len(pdf_reader.pages) - 1:  # Not the last page
                    page_text += "\n"

                # Only process non-empty pages
                if page_text.strip():
                    # Create TextChunk for this page
                    page_chunk = TextChunk(
                        start_index=char_index, end_index=char_index + len(page_text), text=page_text.strip()
                    )

                    # Split the page chunk if it exceeds the size limit
                    for chunk in _split_text_chunk(self.chunk_size_max, page_chunk):
                        yield chunk

                # Always advance the character index by the full page text length
                char_index += len(page_text)
