import tempfile
from typing import Optional
from unittest.mock import patch

import pytest

from server.read.pptx_reader import PptxReader
from server.read.reader import TextChunk


class MockPptxShape:
    """Mock PPTX shape for testing."""

    def __init__(self, text: Optional[str] = None, has_text: bool = True):
        if has_text and text is not None:
            self.text = text
        self._has_text = has_text

    def __hasattr__(self, name):
        if name == "text":
            return self._has_text
        return object.__hasattr__(self, name)


class MockPptxSlide:
    """Mock PPTX slide for testing."""

    def __init__(self, shapes_text: list):
        self.shapes = [MockPptxShape(text) for text in shapes_text]


class MockPptxPresentation:
    """Mock python-pptx Presentation for testing."""

    def __init__(self, slides_data: list):
        self.slides = [MockPptxSlide(shapes) for shapes in slides_data]


class TestPptxReader:
    """Test suite for PptxReader class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        # Clean up temporary files
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_temp_pptx_file(self) -> str:
        """Helper method to create a temporary PPTX file."""
        temp_file = tempfile.NamedTemporaryFile(mode="wb", suffix=".pptx", dir=self.temp_dir, delete=False)
        # Create a minimal PPTX content (ZIP signature)
        temp_file.write(b"PK\x03\x04")  # ZIP file signature
        temp_file.close()
        return temp_file.name

    def test_init_success(self):
        """Test successful initialization of PptxReader."""
        temp_file = self.create_temp_pptx_file()

        with patch("server.read.pptx_reader.Presentation"):
            reader = PptxReader(temp_file)
            assert reader.file_path == temp_file

    @patch("server.read.pptx_reader.Presentation")
    def test_read_simple_presentation(self, mock_presentation):
        """Test reading simple PPTX presentation."""
        temp_file = self.create_temp_pptx_file()

        # Mock Presentation with single slide and shapes
        mock_presentation.return_value = MockPptxPresentation([["Title Slide", "Welcome to the presentation"]])

        reader = PptxReader(temp_file)
        result = reader.read()

        expected = "Title Slide\nWelcome to the presentation\n"
        assert result == expected
        mock_presentation.assert_called_once_with(temp_file)

    @patch("server.read.pptx_reader.Presentation")
    def test_read_multiple_slides(self, mock_presentation):
        """Test reading PPTX presentation with multiple slides."""
        temp_file = self.create_temp_pptx_file()

        # Mock presentation with multiple slides
        mock_presentation.return_value = MockPptxPresentation(
            [["Slide 1 Title", "Slide 1 Content"], ["Slide 2 Title", "Slide 2 Content"], ["Slide 3 Title"]]
        )

        reader = PptxReader(temp_file)
        result = reader.read()

        expected = "Slide 1 Title\nSlide 1 Content\nSlide 2 Title\nSlide 2 Content\nSlide 3 Title\n"
        assert result == expected

    @patch("server.read.pptx_reader.Presentation")
    def test_read_empty_presentation(self, mock_presentation):
        """Test reading empty PPTX presentation."""
        temp_file = self.create_temp_pptx_file()

        # Mock empty presentation
        mock_presentation.return_value = MockPptxPresentation([])

        reader = PptxReader(temp_file)
        result = reader.read()

        assert result == ""

    @patch("server.read.pptx_reader.Presentation")
    def test_read_iter_simple_presentation(self, mock_presentation):
        """Test read_iter with simple PPTX presentation."""
        temp_file = self.create_temp_pptx_file()

        # Mock simple presentation
        mock_presentation.return_value = MockPptxPresentation([["Hello, World!"]])

        reader = PptxReader(temp_file)
        chunks = list(reader.read_iter())

        assert len(chunks) == 1
        assert isinstance(chunks[0], TextChunk)
        assert chunks[0].text == "Hello, World!"
        assert chunks[0].start_index == 0
        assert chunks[0].end_index == len("Hello, World!\n")

    @patch("server.read.pptx_reader.Presentation")
    def test_read_iter_multiple_shapes(self, mock_presentation):
        """Test read_iter with multiple text shapes."""
        temp_file = self.create_temp_pptx_file()

        # Mock presentation with multiple shapes
        mock_presentation.return_value = MockPptxPresentation([["First shape", "Second shape", "Third shape"]])

        reader = PptxReader(temp_file)
        chunks = list(reader.read_iter())

        assert len(chunks) == 3

        # Check first chunk
        assert chunks[0].text == "First shape"
        assert chunks[0].start_index == 0
        expected_end_0 = len("First shape\n")
        assert chunks[0].end_index == expected_end_0

        # Check second chunk
        assert chunks[1].text == "Second shape"
        assert chunks[1].start_index == expected_end_0
        expected_end_1 = expected_end_0 + len("Second shape\n")
        assert chunks[1].end_index == expected_end_1

        # Check third chunk
        assert chunks[2].text == "Third shape"
        assert chunks[2].start_index == expected_end_1
        expected_end_2 = expected_end_1 + len("Third shape\n")
        assert chunks[2].end_index == expected_end_2

    @patch("server.read.pptx_reader.Presentation")
    def test_read_iter_skip_empty_shapes(self, mock_presentation):
        """Test read_iter skips empty text shapes."""
        temp_file = self.create_temp_pptx_file()

        # Mock presentation with empty shapes
        mock_presentation.return_value = MockPptxPresentation([["First shape", "", "   ", "Second shape"]])

        reader = PptxReader(temp_file)
        chunks = list(reader.read_iter())

        # Should only get chunks for non-empty shapes after stripping
        assert len(chunks) == 2
        assert chunks[0].text == "First shape"
        assert chunks[1].text == "Second shape"

    @patch("server.read.pptx_reader.Presentation")
    def test_read_iter_position_consistency(self, mock_presentation):
        """Test that read_iter positions are consistent with read() output."""
        temp_file = self.create_temp_pptx_file()

        shapes = ["First text", "Second text", "Third text"]
        mock_presentation.return_value = MockPptxPresentation([shapes])

        reader = PptxReader(temp_file)

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
        with patch("server.read.pptx_reader.Presentation") as mock_presentation:
            reader = PptxReader("nonexistent_file.pptx")

            # Mock Presentation to raise FileNotFoundError
            mock_presentation.side_effect = FileNotFoundError("File not found")

            with pytest.raises(FileNotFoundError):
                reader.read()

    def test_read_iter_nonexistent_file(self):
        """Test read_iter with nonexistent file raises appropriate error."""
        with patch("server.read.pptx_reader.Presentation") as mock_presentation:
            reader = PptxReader("nonexistent_file.pptx")

            # Mock Presentation to raise FileNotFoundError
            mock_presentation.side_effect = FileNotFoundError("File not found")

            with pytest.raises(FileNotFoundError):
                list(reader.read_iter())

    @patch("server.read.pptx_reader.Presentation")
    def test_text_chunk_properties(self, mock_presentation):
        """Test that TextChunk objects have correct properties."""
        temp_file = self.create_temp_pptx_file()

        mock_presentation.return_value = MockPptxPresentation([["Test content"]])

        reader = PptxReader(temp_file)
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

    @patch("server.read.pptx_reader.Presentation")
    def test_pptx_with_special_characters(self, mock_presentation):
        """Test PPTX processing with special characters."""
        temp_file = self.create_temp_pptx_file()

        special_text = 'Special chars: àáâã & < > " 你好 🌍'
        mock_presentation.return_value = MockPptxPresentation([[special_text]])

        reader = PptxReader(temp_file)

        # Test read method
        result = reader.read()
        assert special_text in result

        # Test read_iter method
        chunks = list(reader.read_iter())
        assert len(chunks) == 1
        assert chunks[0].text == special_text

    @patch("server.read.pptx_reader.Presentation")
    def test_large_pptx_content(self, mock_presentation):
        """Test handling of PPTX with large content."""
        temp_file = self.create_temp_pptx_file()

        # Create large content with multiple slides and shapes
        large_slides = []
        for i in range(20):
            slide_shapes = [f"Slide {i + 1} Title", f"Slide {i + 1} Content: " + "Lorem ipsum dolor sit amet. " * 10]
            large_slides.append(slide_shapes)

        mock_presentation.return_value = MockPptxPresentation(large_slides)

        reader = PptxReader(temp_file)

        # Test read method
        result = reader.read()
        assert len(result) > 2000  # Should be substantial content
        assert "Slide 1 Title" in result
        assert "Slide 20 Title" in result

        # Test read_iter method
        chunks = list(reader.read_iter())
        assert len(chunks) == 40  # 20 slides * 2 shapes each

        # Check that all slide contents are preserved
        all_text = " ".join(chunk.text for chunk in chunks)
        for i in range(20):
            assert f"Slide {i + 1} Title" in all_text

    @patch("server.read.pptx_reader.Presentation")
    def test_pptx_shapes_without_text(self, mock_presentation):
        """Test PPTX processing with shapes that don't have text."""
        temp_file = self.create_temp_pptx_file()

        # Create a mock presentation with mixed shapes
        class MockSlideWithMixedShapes:
            def __init__(self):
                self.shapes = [
                    MockPptxShape("Text shape", has_text=True),
                    MockPptxShape(None, has_text=False),  # Shape without text (e.g., image)
                    MockPptxShape("Another text shape", has_text=True),
                ]

        class MockPresentationWithMixedShapes:
            def __init__(self):
                self.slides = [MockSlideWithMixedShapes()]

        mock_presentation.return_value = MockPresentationWithMixedShapes()

        reader = PptxReader(temp_file)

        # Test read method
        result = reader.read()
        expected = "Text shape\nAnother text shape\n"
        assert result == expected

        # Test read_iter method
        chunks = list(reader.read_iter())
        assert len(chunks) == 2
        assert chunks[0].text == "Text shape"
        assert chunks[1].text == "Another text shape"
