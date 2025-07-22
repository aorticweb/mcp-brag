import tempfile

import pytest

from server.read.text_reader import TextReader


class TestTextReader:
    """Test suite for TextReader class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        # Clean up temporary files
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_temp_text_file(self, content: str) -> str:
        """Helper method to create a temporary text file with given content."""
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", dir=self.temp_dir, delete=False, encoding="utf-8"
        )
        temp_file.write(content)
        temp_file.close()
        return temp_file.name

    def test_init_success(self):
        """Test successful initialization of TextReader."""
        temp_file = self.create_temp_text_file("Test content")
        reader = TextReader(temp_file)
        assert reader.file_path == temp_file
        assert reader.chunk_size_max == 1500  # Default value

    def test_init_with_custom_chunk_size(self):
        """Test initialization with custom chunk size."""
        temp_file = self.create_temp_text_file("Test content")
        reader = TextReader(temp_file, chunk_size_max=300)
        assert reader.file_path == temp_file
        assert reader.chunk_size_max == 300

    def test_read_simple_text(self):
        """Test reading simple text file."""
        content = "Line 1\nLine 2\nLine 3"
        temp_file = self.create_temp_text_file(content)

        reader = TextReader(temp_file)
        result = reader.read()

        assert result == content

    def test_read_empty_file(self):
        """Test reading empty text file."""
        temp_file = self.create_temp_text_file("")

        reader = TextReader(temp_file)
        result = reader.read()

        assert result == ""

    def test_read_iter_simple_text(self):
        """Test read_iter with simple text content."""
        content = "First line\nSecond line\nThird line"
        temp_file = self.create_temp_text_file(content)

        reader = TextReader(temp_file)
        chunks = list(reader.read_iter())

        assert len(chunks) == 3
        assert chunks[0].text == "First line"
        assert chunks[1].text == "Second line"
        assert chunks[2].text == "Third line"

    def test_read_iter_with_empty_lines(self):
        """Test read_iter filters out empty lines."""
        content = "First line\n\nSecond line\n   \nThird line"
        temp_file = self.create_temp_text_file(content)

        reader = TextReader(temp_file)
        chunks = list(reader.read_iter())

        # Should only get chunks for non-empty lines
        assert len(chunks) == 3
        assert chunks[0].text == "First line"
        assert chunks[1].text == "Second line"
        assert chunks[2].text == "Third line"

    def test_read_iter_character_indices(self):
        """Test that read_iter returns accurate character indices."""
        content = "ABC\nDEF\nGHI"
        temp_file = self.create_temp_text_file(content)

        reader = TextReader(temp_file)
        chunks = list(reader.read_iter())

        assert len(chunks) == 3

        # First chunk: "ABC" (positions 0-2)
        assert chunks[0].start_index == 0
        assert chunks[0].end_index == 3
        assert chunks[0].text == "ABC"

        # Second chunk: "DEF" (positions 4-6, accounting for \n)
        assert chunks[1].start_index == 4
        assert chunks[1].end_index == 7
        assert chunks[1].text == "DEF"

        # Third chunk: "GHI" (positions 8-10)
        assert chunks[2].start_index == 8
        assert chunks[2].end_index == 11
        assert chunks[2].text == "GHI"

    def test_read_iter_unicode_handling(self):
        """Test proper handling of Unicode characters."""
        content = "Hello 世界\nCafé ☕\n🚀 Space"
        temp_file = self.create_temp_text_file(content)

        reader = TextReader(temp_file)
        chunks = list(reader.read_iter())

        assert len(chunks) == 3
        assert chunks[0].text == "Hello 世界"
        assert chunks[1].text == "Café ☕"
        assert chunks[2].text == "🚀 Space"

    def test_chunk_size_limit_initialization(self):
        """Test that TextReader properly initializes with custom chunk size limits."""
        temp_file = self.create_temp_text_file("Test content")

        # Test default chunk size
        reader_default = TextReader(temp_file)
        assert reader_default.chunk_size_max == 1500  # Default CHUNK_CHARACTER_LIMIT

        # Test custom chunk size
        reader_custom = TextReader(temp_file, chunk_size_max=100)
        assert reader_custom.chunk_size_max == 100

    def test_line_chunking_with_size_limit(self):
        """Test that long lines are properly split according to chunk_size_max."""
        # Create a very long line that will exceed chunk size limits
        long_line = (
            "This is a very long line that will be repeated many times to create a line that exceeds the maximum chunk size limit. "
            * 10
        )
        content = f"Short line\n{long_line}\nAnother short line"
        temp_file = self.create_temp_text_file(content)

        # Test with small chunk size (100 characters)
        reader = TextReader(temp_file, chunk_size_max=100)
        chunks = list(reader.read_iter())

        # Should have multiple chunks due to the long line
        assert len(chunks) > 3  # At least short line, multiple content chunks, and final line

        # All chunks should respect the size limit
        for chunk in chunks:
            assert len(chunk.text) <= 100, f"Chunk text length {len(chunk.text)} exceeds limit of 100"

        # Verify that we can reconstruct meaningful content from all chunks
        all_chunk_text = " ".join(chunk.text for chunk in chunks)
        assert "Short line" in all_chunk_text
        assert "very long line" in all_chunk_text
        assert "Another short line" in all_chunk_text

    def test_chunking_preserves_word_boundaries(self):
        """Test that chunking tries to preserve word boundaries when possible."""
        # Create a line that will require chunking
        line = "Word1 Word2 Word3 Word4 Word5 Word6 Word7 Word8 Word9 Word10 Word11 Word12"
        content = line
        temp_file = self.create_temp_text_file(content)

        # Use a chunk size that will force splitting but allow for word boundaries
        reader = TextReader(temp_file, chunk_size_max=30)
        chunks = list(reader.read_iter())

        # Should have multiple chunks
        assert len(chunks) > 1

        # Check that words are not broken across chunks (when possible)
        for chunk in chunks:
            words = chunk.text.split()
            for word in words:
                # No word should be cut off (they should be complete)
                assert word.startswith("Word") or not word.startswith("Wor"), f"Word appears to be cut off: '{word}'"

    def test_chunk_indices_accuracy_with_splitting(self):
        """Test that start_index and end_index remain accurate after line splitting."""
        # Create content with long lines that will be split
        long_line = "ABCDEFGHIJKLMNOPQRSTUVWXYZ " * 10  # Create predictable content
        content = f"HEADER\n{long_line}\nFOOTER"
        temp_file = self.create_temp_text_file(content)

        original_content = ""
        with open(temp_file, "r", encoding="utf-8") as f:
            original_content = f.read()

        # Test with small chunk size to force splitting
        reader = TextReader(temp_file, chunk_size_max=50)
        chunks = list(reader.read_iter())

        # Should have multiple chunks
        assert len(chunks) > 2

        # Verify each chunk's indices map correctly to original content
        for i, chunk in enumerate(chunks):
            # Verify indices are within bounds
            assert 0 <= chunk.start_index < len(original_content)
            assert chunk.start_index < chunk.end_index <= len(original_content)

            # Extract the text segment at these indices
            text_segment = original_content[chunk.start_index : chunk.end_index]

            # The text segment should contain the chunk text
            if chunk.text.strip():
                # Account for potential whitespace differences
                assert (
                    chunk.text.strip() in text_segment or text_segment.strip() in chunk.text
                ), f"Chunk text '{chunk.text[:20]}...' not found in text segment '{text_segment[:20]}...'"

    def test_multiple_long_lines_chunking(self):
        """Test chunking behavior with multiple long lines."""
        lines = []
        for i in range(3):
            long_line = f"Line {i}: " + "This is repeated content for line splitting. " * 15
            lines.append(long_line)

        content = "\n".join(lines)
        temp_file = self.create_temp_text_file(content)

        # Test with moderate chunk size
        reader = TextReader(temp_file, chunk_size_max=200)
        chunks = list(reader.read_iter())

        # Should have multiple chunks (more than 3 due to splitting)
        assert len(chunks) > 3

        # Verify all chunks respect size limit
        for chunk in chunks:
            assert len(chunk.text) <= 200

        # Verify content from all lines appears in chunks
        all_text = " ".join(chunk.text for chunk in chunks)
        for i in range(3):
            assert f"Line {i}:" in all_text

    def test_chunk_size_edge_cases(self):
        """Test chunking behavior with edge case chunk sizes."""
        content = "This is a test line with some content"
        temp_file = self.create_temp_text_file(content)

        # Test with very small chunk size
        reader_tiny = TextReader(temp_file, chunk_size_max=5)
        chunks_tiny = list(reader_tiny.read_iter())

        # Should create multiple very small chunks
        assert len(chunks_tiny) > 1
        for chunk in chunks_tiny:
            assert len(chunk.text) <= 5

        # Test with very large chunk size
        reader_large = TextReader(temp_file, chunk_size_max=10000)
        chunks_large = list(reader_large.read_iter())

        # Should have fewer, larger chunks
        assert len(chunks_large) <= len(chunks_tiny)

        # Verify all chunks respect their respective size limits
        for chunk in chunks_large:
            assert len(chunk.text) <= 10000

    def test_read_nonexistent_file(self):
        """Test reading nonexistent file raises appropriate error."""
        reader = TextReader("nonexistent_file.txt")

        with pytest.raises(FileNotFoundError):
            reader.read()

    def test_read_iter_nonexistent_file(self):
        """Test read_iter with nonexistent file raises appropriate error."""
        reader = TextReader("nonexistent_file.txt")

        with pytest.raises(FileNotFoundError):
            list(reader.read_iter())

    def test_large_file_handling(self):
        """Test handling of larger text files."""
        # Create a larger text content
        lines = []
        for i in range(50):
            lines.append(f"Line {i}: This is some content to make the file larger and test performance.")

        content = "\n".join(lines)
        temp_file = self.create_temp_text_file(content)

        reader = TextReader(temp_file)

        # Test read method
        result = reader.read()
        assert len(result) == len(content)

        # Test read_iter method
        chunks = list(reader.read_iter())
        assert len(chunks) == 50  # One chunk per line

        # Should contain all line content
        all_text = " ".join(chunk.text for chunk in chunks)
        assert "Line 0:" in all_text
        assert "Line 49:" in all_text
