import tempfile
from unittest.mock import patch

import pytest

from server.read.pdf_reader import PDFReader
from server.read.reader import TextChunk


class MockPDFPage:
    """Mock PDF page for testing."""

    def __init__(self, text: str):
        self.text = text

    def extract_text(self) -> str:
        return self.text


class MockPDFReader:
    """Mock PyPDF2.PdfReader for testing."""

    def __init__(self, pages_text: list):
        self.pages = [MockPDFPage(text) for text in pages_text]


class TestPDFReader:
    """Test suite for PDFReader class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        # Clean up temporary files
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_temp_pdf_file(self) -> str:
        """Helper method to create a temporary PDF file."""
        temp_file = tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", dir=self.temp_dir, delete=False)
        # Create a minimal PDF content (not a real PDF, just for file existence)
        temp_file.write(b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n")
        temp_file.close()
        return temp_file.name

    def test_init_success(self):
        """Test successful initialization of PDFReader."""
        temp_file = self.create_temp_pdf_file()
        reader = PDFReader(temp_file)
        assert reader.file_path == temp_file

    @patch("server.read.pdf_reader.PyPDF2.PdfReader")
    def test_read_single_page(self, mock_pdf_reader):
        """Test reading PDF with single page."""
        temp_file = self.create_temp_pdf_file()

        # Mock PyPDF2.PdfReader
        mock_pdf_reader.return_value = MockPDFReader(["Hello, World!"])

        reader = PDFReader(temp_file)
        result = reader.read()

        assert result == "Hello, World!\n"

    @patch("server.read.pdf_reader.PyPDF2.PdfReader")
    def test_read_multiple_pages(self, mock_pdf_reader):
        """Test reading PDF with multiple pages."""
        temp_file = self.create_temp_pdf_file()

        # Mock PyPDF2.PdfReader with multiple pages
        mock_pdf_reader.return_value = MockPDFReader(["Page 1 content", "Page 2 content", "Page 3 content"])

        reader = PDFReader(temp_file)
        result = reader.read()

        expected = "Page 1 content\nPage 2 content\nPage 3 content\n"
        assert result == expected

    @patch("server.read.pdf_reader.PyPDF2.PdfReader")
    def test_read_empty_pages(self, mock_pdf_reader):
        """Test reading PDF with empty pages."""
        temp_file = self.create_temp_pdf_file()

        # Mock PyPDF2.PdfReader with empty pages
        mock_pdf_reader.return_value = MockPDFReader(["", "   ", "Content"])

        reader = PDFReader(temp_file)
        result = reader.read()

        expected = "\n   \nContent\n"
        assert result == expected

    @patch("server.read.pdf_reader.PyPDF2.PdfReader")
    def test_read_iter_single_page(self, mock_pdf_reader):
        """Test read_iter with single page PDF."""
        temp_file = self.create_temp_pdf_file()

        # Mock PyPDF2.PdfReader
        mock_pdf_reader.return_value = MockPDFReader(["Hello, World!"])

        reader = PDFReader(temp_file)
        chunks = list(reader.read_iter())

        assert len(chunks) == 1
        assert isinstance(chunks[0], TextChunk)
        assert chunks[0].text == "Hello, World!"
        assert chunks[0].start_index == 0
        assert chunks[0].end_index == len("Hello, World!")

    @patch("server.read.pdf_reader.PyPDF2.PdfReader")
    def test_read_iter_multiple_pages(self, mock_pdf_reader):
        """Test read_iter with multiple pages."""
        temp_file = self.create_temp_pdf_file()

        # Mock PyPDF2.PdfReader with multiple pages
        pages_content = ["Page 1 content", "Page 2 content", "Page 3 content"]
        mock_pdf_reader.return_value = MockPDFReader(pages_content)

        reader = PDFReader(temp_file)
        chunks = list(reader.read_iter())

        assert len(chunks) == 3

        # Check first chunk
        assert chunks[0].text == "Page 1 content"
        assert chunks[0].start_index == 0
        expected_end_0 = len("Page 1 content\n")  # includes newline
        assert chunks[0].end_index == expected_end_0

        # Check second chunk
        assert chunks[1].text == "Page 2 content"
        assert chunks[1].start_index == expected_end_0
        expected_end_1 = expected_end_0 + len("Page 2 content\n")
        assert chunks[1].end_index == expected_end_1

        # Check third chunk (last page, no newline added)
        assert chunks[2].text == "Page 3 content"
        assert chunks[2].start_index == expected_end_1
        expected_end_2 = expected_end_1 + len("Page 3 content")
        assert chunks[2].end_index == expected_end_2

    @patch("server.read.pdf_reader.PyPDF2.PdfReader")
    def test_read_iter_skip_empty_pages(self, mock_pdf_reader):
        """Test read_iter skips empty pages."""
        temp_file = self.create_temp_pdf_file()

        # Mock PyPDF2.PdfReader with some empty pages
        mock_pdf_reader.return_value = MockPDFReader(
            ["Page 1 content", "", "   ", "Page 4 content"]  # Empty page  # Whitespace only
        )

        reader = PDFReader(temp_file)
        chunks = list(reader.read_iter())

        # Should only get chunks for non-empty pages after stripping
        assert len(chunks) == 2
        assert chunks[0].text == "Page 1 content"
        assert chunks[1].text == "Page 4 content"

    @patch("server.read.pdf_reader.PyPDF2.PdfReader")
    def test_read_iter_position_consistency(self, mock_pdf_reader):
        """Test that read_iter positions are consistent with read() output."""
        temp_file = self.create_temp_pdf_file()

        pages_content = ["First page", "Second page", "Third page"]
        mock_pdf_reader.return_value = MockPDFReader(pages_content)

        reader = PDFReader(temp_file)

        # Get full text
        full_text = reader.read()

        # Get chunks
        chunks = list(reader.read_iter())

        # Verify that extracting text using chunk indices matches chunk text
        for chunk in chunks:
            # Extract text from full content using chunk indices
            extracted_text = full_text[chunk.start_index : chunk.end_index]
            # The extracted text should contain the chunk text (after stripping)
            assert chunk.text in extracted_text or extracted_text.strip() == chunk.text

    def test_read_nonexistent_file(self):
        """Test reading nonexistent file raises appropriate error."""
        reader = PDFReader("nonexistent_file.pdf")

        with pytest.raises(FileNotFoundError):
            reader.read()

    def test_read_iter_nonexistent_file(self):
        """Test read_iter with nonexistent file raises appropriate error."""
        reader = PDFReader("nonexistent_file.pdf")

        with pytest.raises(FileNotFoundError):
            list(reader.read_iter())

    @patch("server.read.pdf_reader.PyPDF2.PdfReader")
    def test_text_chunk_properties(self, mock_pdf_reader):
        """Test that TextChunk objects have correct properties."""
        temp_file = self.create_temp_pdf_file()

        mock_pdf_reader.return_value = MockPDFReader(["Test content"])

        reader = PDFReader(temp_file)
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

    @patch("server.read.pdf_reader.PyPDF2.PdfReader")
    def test_pdf_with_special_characters(self, mock_pdf_reader):
        """Test PDF processing with special characters."""
        temp_file = self.create_temp_pdf_file()

        special_text = 'Special chars: àáâã & < > " 你好 🌍'
        mock_pdf_reader.return_value = MockPDFReader([special_text])

        reader = PDFReader(temp_file)

        # Test read method
        result = reader.read()
        assert special_text in result

        # Test read_iter method
        chunks = list(reader.read_iter())
        assert len(chunks) == 1
        assert chunks[0].text == special_text

    @patch("server.read.pdf_reader.PyPDF2.PdfReader")
    def test_large_pdf_content(self, mock_pdf_reader):
        """Test handling of PDF with large content."""
        temp_file = self.create_temp_pdf_file()

        # Create large content
        large_pages = []
        for i in range(10):
            page_content = f"Page {i + 1}: " + "Lorem ipsum dolor sit amet. " * 50
            large_pages.append(page_content)

        mock_pdf_reader.return_value = MockPDFReader(large_pages)

        reader = PDFReader(temp_file)

        # Test read method
        result = reader.read()
        assert len(result) > 1000  # Should be substantial content
        assert "Page 1:" in result
        assert "Page 10:" in result

        # Test read_iter method
        chunks = list(reader.read_iter())
        assert len(chunks) == 10

        # Check that all page contents are preserved
        all_text = " ".join(chunk.text for chunk in chunks)
        for i in range(10):
            assert f"Page {i + 1}:" in all_text
