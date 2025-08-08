from typing import Iterator

from server.constants import CHUNK_CHARACTER_LIMIT
from server.read.reader import Reader, SourceType, TextChunk


class TextReader(Reader):
    file_path: str
    chunk_size_max: int

    def __init__(self, file_path: str, chunk_size_max: int = CHUNK_CHARACTER_LIMIT.value):
        self.file_path = file_path
        self.chunk_size_max = chunk_size_max

    def source_type(self) -> SourceType:
        return SourceType.LOCAL_TEXT_FILE

    def read(self) -> str:
        with open(self.file_path, "r", encoding="utf-8", errors="replace") as file:
            return file.read()

    def read_iter(self) -> Iterator[TextChunk]:
        """
        Read the file line by line and yield TextChunk objects.

        Each line becomes a TextChunk with start_index and end_index representing
        the character positions at the start and end of the line in the original file.
        If a line exceeds the chunk_size_max, it will be split into multiple chunks
        while maintaining accurate character indices.

        Yields:
            TextChunk: Chunk containing line text and its character indices
        """
        char_index = 0

        with open(self.file_path, "r", encoding="utf-8", errors="replace") as file:
            for line in file:
                line_length = len(line)

                # Only process non-empty lines (after stripping)
                if line.strip():
                    # Create a TextChunk for this line
                    line_text = line.rstrip("\n\r")  # Remove trailing newlines but keep the text
                    line_chunk = TextChunk(
                        start_index=char_index, end_index=char_index + len(line_text), text=line_text
                    )

                    # Split the line chunk if it exceeds the size limit
                    for chunk in _split_text_chunk(self.chunk_size_max, line_chunk):
                        yield chunk

                # Always advance the character index by the full line length
                # (including newline characters)
                char_index += line_length


def _split_text_chunk(chunk_size_max: int, text_chunk: TextChunk) -> Iterator[TextChunk]:
    """
    Split a text chunk into smaller chunks that respect the chunk_size_max limit.

    The start_index and end_index are calculated to maintain correct positions
    relative to the original text file.

    Args:
        text_chunk: The TextChunk to potentially split

    Yields:
        TextChunk: Smaller chunks with correct indices
    """
    text = text_chunk.text
    if len(text) <= chunk_size_max:
        # Chunk is already within the limit
        yield text_chunk
        return

    # Split the text into smaller chunks
    start_pos = 0
    original_start = text_chunk.start_index

    while start_pos < len(text):
        end_pos = min(start_pos + chunk_size_max, len(text))

        # Try to break at word boundaries to avoid splitting words
        if end_pos < len(text):
            # Look for the last space within the chunk
            last_space = text.rfind(" ", start_pos, end_pos)
            if last_space > start_pos:
                end_pos = last_space

        chunk_text = text[start_pos:end_pos].strip()

        if chunk_text:  # Only yield non-empty chunks
            # Calculate the actual character positions in the original file
            chunk_start = original_start + start_pos
            chunk_end = original_start + end_pos

            yield TextChunk(start_index=chunk_start, end_index=chunk_end, text=chunk_text)

        start_pos = end_pos
        # Skip any whitespace at the beginning of the next chunk
        while start_pos < len(text) and text[start_pos].isspace():
            start_pos += 1
