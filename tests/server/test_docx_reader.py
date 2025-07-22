import tempfile
from unittest.mock import patch

import pytest

from server.read.docx_reader import DocxReader
from server.read.reader import TextChunk


class MockDocxParagraph:
    """Mock DOCX paragraph for testing."""

    def __init__(self, text: str):
        self.text = text


class MockDocxDocument:
    """Mock python-docx Document for testing."""

    def __init__(self, paragraphs_text: list):
        self.paragraphs = [MockDocxParagraph(text) for text in paragraphs_text]


class TestDocxReader:
    """Test suite for DocxReader class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        # Clean up temporary files
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_temp_docx_file(self) -> str:
        """Helper method to create a temporary DOCX file."""
        temp_file = tempfile.NamedTemporaryFile(mode="wb", suffix=".docx", dir=self.temp_dir, delete=False)
        # Create a minimal DOCX content (ZIP signature)
        temp_file.write(b"PK\x03\x04")  # ZIP file signature
        temp_file.close()
        return temp_file.name

    def test_init_success(self):
        """Test successful initialization of DocxReader."""
        temp_file = self.create_temp_docx_file()

        with patch("server.read.docx_reader.Document"):
            reader = DocxReader(temp_file)
            assert reader.file_path == temp_file

    @patch("server.read.docx_reader.Document")
    def test_read_simple_document(self, mock_document):
        """Test reading simple DOCX document."""
        temp_file = self.create_temp_docx_file()

        # Mock Document
        mock_document.return_value = MockDocxDocument(["Hello, World!", "This is a test document."])

        reader = DocxReader(temp_file)
        result = reader.read()

        expected = "Hello, World!\nThis is a test document.\n"
        assert result == expected
        mock_document.assert_called_once_with(temp_file)

    @patch("server.read.docx_reader.Document")
    def test_read_multiline_document(self, mock_document):
        """Test reading DOCX document with multiple paragraphs."""
        temp_file = self.create_temp_docx_file()

        # Mock multiline document
        paragraphs = ["First paragraph", "Second paragraph", "Third paragraph"]
        mock_document.return_value = MockDocxDocument(paragraphs)

        reader = DocxReader(temp_file)
        result = reader.read()

        expected = "First paragraph\nSecond paragraph\nThird paragraph\n"
        assert result == expected

    @patch("server.read.docx_reader.Document")
    def test_read_empty_document(self, mock_document):
        """Test reading empty DOCX document."""
        temp_file = self.create_temp_docx_file()

        # Mock empty document
        mock_document.return_value = MockDocxDocument([])

        reader = DocxReader(temp_file)
        result = reader.read()

        assert result == ""

    @patch("server.read.docx_reader.Document")
    def test_read_iter_simple_document(self, mock_document):
        """Test read_iter with simple DOCX document."""
        temp_file = self.create_temp_docx_file()

        # Mock simple document
        mock_document.return_value = MockDocxDocument(["Hello, World!"])

        reader = DocxReader(temp_file)
        chunks = list(reader.read_iter())

        assert len(chunks) == 1
        assert isinstance(chunks[0], TextChunk)
        assert chunks[0].text == "Hello, World!"
        assert chunks[0].start_index == 0
        assert chunks[0].end_index == len("Hello, World!\n")

    @patch("server.read.docx_reader.Document")
    def test_read_iter_multiple_paragraphs(self, mock_document):
        """Test read_iter with multiple paragraphs."""
        temp_file = self.create_temp_docx_file()

        # Mock multiline document
        paragraphs = ["First paragraph", "Second paragraph", "Third paragraph"]
        mock_document.return_value = MockDocxDocument(paragraphs)

        reader = DocxReader(temp_file)
        chunks = list(reader.read_iter())

        assert len(chunks) == 3

        # Check first chunk
        assert chunks[0].text == "First paragraph"
        assert chunks[0].start_index == 0
        expected_end_0 = len("First paragraph\n")
        assert chunks[0].end_index == expected_end_0

        # Check second chunk
        assert chunks[1].text == "Second paragraph"
        assert chunks[1].start_index == expected_end_0
        expected_end_1 = expected_end_0 + len("Second paragraph\n")
        assert chunks[1].end_index == expected_end_1

        # Check third chunk
        assert chunks[2].text == "Third paragraph"
        assert chunks[2].start_index == expected_end_1
        expected_end_2 = expected_end_1 + len("Third paragraph\n")
        assert chunks[2].end_index == expected_end_2

    @patch("server.read.docx_reader.Document")
    def test_read_iter_skip_empty_paragraphs(self, mock_document):
        """Test read_iter skips empty paragraphs."""
        temp_file = self.create_temp_docx_file()

        # Mock document with empty paragraphs
        mock_document.return_value = MockDocxDocument(
            ["First paragraph", "", "   ", "Second paragraph"]  # Empty paragraph  # Whitespace only
        )

        reader = DocxReader(temp_file)
        chunks = list(reader.read_iter())

        # Should only get chunks for non-empty paragraphs after stripping
        assert len(chunks) == 2
        assert chunks[0].text == "First paragraph"
        assert chunks[1].text == "Second paragraph"

    @patch("server.read.docx_reader.Document")
    def test_read_iter_position_consistency(self, mock_document):
        """Test that read_iter positions are consistent with read() output."""
        temp_file = self.create_temp_docx_file()

        paragraphs = ["First line", "Second line", "Third line"]
        mock_document.return_value = MockDocxDocument(paragraphs)

        reader = DocxReader(temp_file)

        # Get full text
        full_text = reader.read()

        # Get chunks
        chunks = list(reader.read_iter())

        # Verify that extracting text using chunk indices gives consistent results
        for chunk in chunks:
            # Extract text from full content using chunk indices
            extracted_text = full_text[chunk.start_index : chunk.end_index]
            # The extracted text should contain the chunk text
            assert chunk.text in extracted_text or extracted_text.strip() == chunk.text

    def test_read_nonexistent_file(self):
        """Test reading nonexistent file raises appropriate error."""
        with patch("server.read.docx_reader.Document") as mock_document:
            reader = DocxReader("nonexistent_file.docx")

            # Mock Document to raise FileNotFoundError
            mock_document.side_effect = FileNotFoundError("File not found")

            with pytest.raises(FileNotFoundError):
                reader.read()

    def test_read_iter_nonexistent_file(self):
        """Test read_iter with nonexistent file raises appropriate error."""
        with patch("server.read.docx_reader.Document") as mock_document:
            reader = DocxReader("nonexistent_file.docx")

            # Mock Document to raise FileNotFoundError
            mock_document.side_effect = FileNotFoundError("File not found")

            with pytest.raises(FileNotFoundError):
                list(reader.read_iter())

    @patch("server.read.docx_reader.Document")
    def test_text_chunk_properties(self, mock_document):
        """Test that TextChunk objects have correct properties."""
        temp_file = self.create_temp_docx_file()

        mock_document.return_value = MockDocxDocument(["Test content"])

        reader = DocxReader(temp_file)
        chunks = list(reader.read_iter())

        assert len(chunks) == 1
        chunk = chunks[0]

        # Test TextChunk interface
        assert hasattr(chunk, "start_index")
        assert hasattr(chunk, "end_index")
        assert hasattr(chunk, "text")
        assert hasattr(chunk, "to_dict")

        # Test types
        assert isinstance(chunk.start_index, int)
        assert isinstance(chunk.end_index, int)
        assert isinstance(chunk.text, str)

        # Test to_dict method
        chunk_dict = chunk.to_dict()
        assert "start_index" in chunk_dict
        assert "end_index" in chunk_dict
        assert "text" in chunk_dict

    @patch("server.read.docx_reader.Document")
    def test_docx_with_special_characters(self, mock_document):
        """Test DOCX processing with special characters."""
        temp_file = self.create_temp_docx_file()

        special_text = 'Special chars: àáâã & < > " 你好 🌍'
        mock_document.return_value = MockDocxDocument([special_text])

        reader = DocxReader(temp_file)

        # Test read method
        result = reader.read()
        assert special_text in result

        # Test read_iter method
        chunks = list(reader.read_iter())
        assert len(chunks) == 1
        assert chunks[0].text == special_text

    @patch("server.read.docx_reader.Document")
    def test_large_docx_content(self, mock_document):
        """Test handling of DOCX with large content."""
        temp_file = self.create_temp_docx_file()

        # Create large content with multiple paragraphs
        large_paragraphs = []
        for i in range(50):
            paragraph = f"Paragraph {i + 1}: " + "Lorem ipsum dolor sit amet. " * 20
            large_paragraphs.append(paragraph)

        mock_document.return_value = MockDocxDocument(large_paragraphs)

        reader = DocxReader(temp_file)

        # Test read method
        result = reader.read()
        assert len(result) > 5000  # Should be substantial content
        assert "Paragraph 1:" in result
        assert "Paragraph 50:" in result

        # Test read_iter method
        chunks = list(reader.read_iter())
        assert len(chunks) == 50

        # Check that all paragraph contents are preserved
        all_text = " ".join(chunk.text for chunk in chunks)
        for i in range(50):
            assert f"Paragraph {i + 1}:" in all_text
