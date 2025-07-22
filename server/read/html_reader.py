import re
from typing import Iterator, List, Tuple

from bs4 import BeautifulSoup

from server.constants import CHUNK_CHARACTER_LIMIT
from server.read.reader import Reader, SourceType, TextChunk


class HTMLReader(Reader):
    file_path: str
    chunk_size_max: int

    def __init__(self, file_path: str, chunk_size_max: int = CHUNK_CHARACTER_LIMIT.value):
        self.file_path = file_path
        self.chunk_size_max = chunk_size_max

    def source_type(self) -> SourceType:
        return SourceType.LOCAL_HTML_FILE

    def read(self) -> str:
        """
        Read the HTML file and return the original HTML content without any modifications.

        Returns:
            str: The original HTML content including all tags, scripts, styles, etc.
        """
        with open(self.file_path, "r", encoding="utf-8") as file:
            return file.read()

    def read_iter(self) -> Iterator[TextChunk]:
        """
        Read the HTML file and yield TextChunk objects for text content.

        The start_index and end_index correspond to the character positions
        in the original HTML content (including tags), while the text contains
        only the extracted text content split into chunks respecting the size limit.

        Yields:
            TextChunk: Chunk containing extracted text and its original HTML indices
        """
        with open(self.file_path, "r", encoding="utf-8") as file:
            html_content = file.read()

        # Extract text chunks with accurate position tracking
        for text_chunk in self._extract_text_with_accurate_positions(html_content):
            if text_chunk.text.strip():  # Only yield non-empty text chunks
                # Split large chunks into smaller ones respecting the size limit
                for chunked_segment in self._split_text_chunk(text_chunk):
                    yield chunked_segment

    def _extract_text_with_accurate_positions(self, html_content: str) -> Iterator[TextChunk]:
        """
        Extract text content while accurately maintaining original HTML character positions.

        This method uses BeautifulSoup to extract text nodes and maps their positions
        back to the original HTML content.

        Args:
            html_content: The original HTML content

        Yields:
            TextChunk: Text chunks with accurate original HTML positions
        """
        # Extract text segments with position tracking
        text_segments = self._parse_html_for_text_segments(html_content, "")

        for start_pos, end_pos, text_content in text_segments:
            # Clean up whitespace while preserving meaningful content
            cleaned_text = re.sub(r"\s+", " ", text_content).strip()
            if cleaned_text:
                yield TextChunk(start_index=start_pos, end_index=end_pos, text=cleaned_text)

    def _parse_html_for_text_segments(self, original_html: str, cleaned_html: str) -> List[Tuple[int, int, str]]:
        """
        Parse HTML to extract text segments with their original positions.

        Args:
            original_html: The original HTML content
            cleaned_html: HTML with script/style tags removed (unused - kept for interface compatibility)

        Returns:
            List of tuples (start_pos, end_pos, text_content)
        """
        text_segments = []

        # Parse the original HTML
        soup = BeautifulSoup(original_html, "html.parser")

        # Remove script and style tags
        for element in soup(["script", "style"]):
            element.decompose()

        # Extract all text nodes with their content
        text_nodes = []
        for element in soup.find_all(string=True):
            text_content = str(element).strip()
            if text_content:  # Only process non-empty text
                text_nodes.append(text_content)

        # Find each text segment's position in the original HTML
        search_start = 0
        for text_content in text_nodes:
            # Find the position of this text in the original HTML
            original_pos = self._find_text_position(original_html, text_content, search_start)

            if original_pos >= 0:
                text_segments.append((original_pos, original_pos + len(text_content), text_content))
                # Update search start to avoid finding the same text again
                search_start = original_pos + len(text_content)

        return text_segments

    def _find_text_position(self, html_content: str, text_content: str, start_from: int = 0) -> int:
        """
        Find the position of text content in HTML, ensuring it's not inside a tag.

        Args:
            html_content: The HTML content to search in
            text_content: The text to find
            start_from: Position to start searching from

        Returns:
            int: Position of the text in HTML, or -1 if not found
        """
        if not text_content.strip():
            return -1

        current_pos = start_from
        while current_pos < len(html_content):
            # Find the next occurrence of the text
            found_pos = html_content.find(text_content, current_pos)
            if found_pos == -1:
                break

            # Check if this position is inside a tag
            if not self._is_inside_tag(html_content, found_pos):
                return found_pos

            # Move past this occurrence and continue searching
            current_pos = found_pos + 1

        return -1

    def _is_inside_tag(self, html_content: str, position: int) -> bool:
        """
        Check if a position in HTML is inside a tag (between < and >).

        Args:
            html_content: HTML content
            position: Character position to check

        Returns:
            bool: True if position is inside a tag
        """
        # Look backwards for < and >
        last_open = html_content.rfind("<", 0, position)
        last_close = html_content.rfind(">", 0, position)

        # If the last < comes after the last >, we're inside a tag
        return last_open > last_close

    def _split_text_chunk(self, text_chunk: TextChunk) -> Iterator[TextChunk]:
        """
        Split a text chunk into smaller chunks that respect the chunk_size_max limit.

        The start_index and end_index are calculated to maintain correct positions
        relative to the original HTML content.

        Args:
            text_chunk: The TextChunk to potentially split

        Yields:
            TextChunk: Smaller chunks with correct indices
        """
        text = text_chunk.text
        if len(text) <= self.chunk_size_max:
            # Chunk is already within the limit
            yield text_chunk
            return

        # Split the text into smaller chunks
        start_pos = 0
        original_start = text_chunk.start_index
        original_text_length = len(text)
        original_html_length = text_chunk.end_index - text_chunk.start_index

        while start_pos < len(text):
            end_pos = min(start_pos + self.chunk_size_max, len(text))

            # Try to break at word boundaries to avoid splitting words
            if end_pos < len(text):
                # Look for the last space within the chunk
                last_space = text.rfind(" ", start_pos, end_pos)
                if last_space > start_pos:
                    end_pos = last_space

            chunk_text = text[start_pos:end_pos].strip()

            if chunk_text:  # Only yield non-empty chunks
                # Calculate the proportional HTML indices
                # This is an approximation since HTML tags don't map directly to text
                text_start_ratio = start_pos / original_text_length
                text_end_ratio = end_pos / original_text_length

                html_chunk_start = original_start + int(text_start_ratio * original_html_length)
                html_chunk_end = original_start + int(text_end_ratio * original_html_length)

                yield TextChunk(start_index=html_chunk_start, end_index=html_chunk_end, text=chunk_text)

            start_pos = end_pos
            # Skip any whitespace at the beginning of the next chunk
            while start_pos < len(text) and text[start_pos].isspace():
                start_pos += 1
