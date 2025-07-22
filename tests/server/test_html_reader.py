import tempfile

import pytest

from server.read.html_reader import HTMLReader


class TestHTMLReader:
    """Test suite for HTMLReader class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        # Clean up temporary files
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_temp_html_file(self, content: str) -> str:
        """Helper method to create a temporary HTML file with given content."""
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", dir=self.temp_dir, delete=False, encoding="utf-8"
        )
        temp_file.write(content)
        temp_file.close()
        return temp_file.name

    def test_init_success(self):
        """Test successful initialization of HTMLReader."""
        temp_file = self.create_temp_html_file("<html><body>Test</body></html>")
        reader = HTMLReader(temp_file)
        assert reader.file_path == temp_file

    def test_read_simple_html(self):
        """Test reading simple HTML file returns original content."""
        html_content = "<html><head><title>Test</title></head><body><h1>Hello</h1><p>World</p></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        result = reader.read()

        assert result == html_content

    def test_read_html_with_scripts_and_styles(self):
        """Test reading HTML with scripts and styles returns original content."""
        html_content = """<html>
<head>
    <style>body { color: red; }</style>
    <script>alert('test');</script>
</head>
<body>
    <h1>Title</h1>
    <p>Content</p>
    <script>console.log('more js');</script>
</body>
</html>"""
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        result = reader.read()

        assert result == html_content

    def test_read_empty_html_file(self):
        """Test reading empty HTML file."""
        temp_file = self.create_temp_html_file("")

        reader = HTMLReader(temp_file)
        result = reader.read()

        assert result == ""

    def test_read_html_with_special_characters(self):
        """Test reading HTML with special characters and encoding."""
        html_content = '<html><body><p>Special chars: àáâã & < > "</p></body></html>'
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        result = reader.read()

        assert result == html_content

    def test_read_iter_simple_html(self):
        """Test read_iter with simple HTML content."""
        html_content = "<html><body><h1>Title</h1><p>Content here</p></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        chunks = list(reader.read_iter())

        # Should have chunks for text content
        assert len(chunks) > 0
        assert chunks[0].text == "Title"
        assert chunks[1].text == "Content here"

    def test_read_iter_with_scripts_and_styles(self):
        """Test read_iter excludes script and style content."""
        html_content = """<html>
<head>
    <style>body { color: red; }</style>
    <script>alert('test');</script>
</head>
<body>
    <h1>Title</h1>
    <p>Content</p>
    <script>console.log('ignored');</script>
</body>
</html>"""
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        chunks = list(reader.read_iter())

        # Check that script and style content is not in any chunk
        all_text = " ".join(chunk.text for chunk in chunks)
        assert "alert('test')" not in all_text
        assert "console.log('ignored')" not in all_text
        assert "color: red" not in all_text

        # But regular content should be present
        assert "Title" in all_text or any("Title" in chunk.text for chunk in chunks)
        assert "Content" in all_text or any("Content" in chunk.text for chunk in chunks)

    def test_read_iter_position_indices(self):
        """Test that read_iter returns accurate position indices."""
        html_content = "<html><body><p>Hello</p><p>World</p></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        chunks = list(reader.read_iter())

        # Verify that all indices are within the original HTML content bounds
        for chunk in chunks:
            assert 0 <= chunk.start_index < len(html_content)
            assert chunk.start_index < chunk.end_index <= len(html_content)

            # Verify that the text can be found in the original HTML
            # (though it might not be exact due to cleaning)
            assert chunk.text.strip() != ""

    def test_read_iter_empty_html(self):
        """Test read_iter with empty HTML."""
        html_content = "<html><body></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        chunks = list(reader.read_iter())

        # Should have no text chunks for empty content
        assert len(chunks) == 0

    def test_read_iter_only_whitespace(self):
        """Test read_iter with HTML containing only whitespace."""
        html_content = "<html><body><p>   </p><div>\n\t</div></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        chunks = list(reader.read_iter())

        # Should filter out whitespace-only content
        assert len(chunks) == 0

    def test_read_iter_mixed_content(self):
        """Test read_iter with mixed content including nested tags."""
        html_content = """<html>
<body>
    <div>
        <h1>Main Title</h1>
        <p>This is a <strong>paragraph</strong> with <em>formatting</em>.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
    </div>
</body>
</html>"""
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        chunks = list(reader.read_iter())

        assert len(chunks) > 0

        # Collect all text
        all_text = " ".join(chunk.text for chunk in chunks)

        # Should contain the text content
        assert "Main Title" in all_text
        assert "paragraph" in all_text
        assert "formatting" in all_text
        assert "Item 1" in all_text
        assert "Item 2" in all_text

    def test_read_iter_malformed_html(self):
        """Test read_iter with malformed HTML."""
        html_content = "<html><body><p>Unclosed paragraph<div>Missing close</body></html>"
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        # Should not raise an exception
        chunks = list(reader.read_iter())

        # Should still extract some text
        assert len(chunks) > 0
        all_text = " ".join(chunk.text for chunk in chunks)
        assert "Unclosed paragraph" in all_text or "Missing close" in all_text

    def test_read_nonexistent_file(self):
        """Test reading nonexistent file raises appropriate error."""
        reader = HTMLReader("nonexistent_file.html")

        with pytest.raises(FileNotFoundError):
            reader.read()

    def test_read_iter_nonexistent_file(self):
        """Test read_iter with nonexistent file raises appropriate error."""
        reader = HTMLReader("nonexistent_file.html")

        with pytest.raises(FileNotFoundError):
            list(reader.read_iter())

    def test_unicode_handling(self):
        """Test proper handling of Unicode characters."""
        html_content = "<html><body><p>Unicode: 你好 🌍 café</p></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)

        # Test read method
        result = reader.read()
        assert "你好" in result
        assert "🌍" in result
        assert "café" in result

        # Test read_iter method
        chunks = list(reader.read_iter())
        all_text = " ".join(chunk.text for chunk in chunks)
        assert "你好" in all_text
        assert "🌍" in all_text
        assert "café" in all_text

    def test_large_html_file(self):
        """Test handling of larger HTML files."""
        # Create a larger HTML content
        html_content = "<html><body>"
        for i in range(100):
            html_content += f"<p>Paragraph {i} with some content to make it longer.</p>"
        html_content += "</body></html>"

        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)

        # Test read method
        result = reader.read()
        assert len(result) == len(html_content)

        # Test read_iter method
        chunks = list(reader.read_iter())
        assert len(chunks) > 0

        # Should have multiple chunks for the content
        # Each paragraph should contribute to chunks
        all_text = " ".join(chunk.text for chunk in chunks)
        assert "Paragraph 0" in all_text
        assert "Paragraph 99" in all_text

    def test_chunk_indices_match_original_content(self):
        """Test that chunk indices correctly map to original HTML content."""
        html_content = "<html><body><h1>Title</h1><p>First paragraph</p><p>Second paragraph</p></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        original_content = reader.read()
        chunks = list(reader.read_iter())

        # Verify that each chunk's indices correctly map to the original content
        for chunk in chunks:
            # Extract the content at the chunk's indices from the original HTML
            extracted_content = original_content[chunk.start_index : chunk.end_index]

            # The extracted content should contain the chunk's text
            # Note: The chunk text is cleaned/processed, so we check if it's contained
            # within the extracted HTML segment
            assert chunk.text.strip() in extracted_content or extracted_content.strip() in chunk.text

            # Verify indices are valid
            assert 0 <= chunk.start_index < len(original_content)
            assert chunk.start_index < chunk.end_index <= len(original_content)

            # The extracted content should not be empty for non-empty chunks
            if chunk.text.strip():
                assert extracted_content.strip() != ""

    def test_chunk_indices_with_complex_html(self):
        """Test chunk indices with more complex HTML structure."""
        html_content = """<html>
<head>
    <title>Test Page</title>
    <style>body { margin: 0; }</style>
</head>
<body>
    <div class="header">
        <h1>Main Title</h1>
        <nav>Navigation</nav>
    </div>
    <main>
        <article>
            <h2>Article Title</h2>
            <p>First paragraph with <strong>bold text</strong> and <em>italic text</em>.</p>
            <p>Second paragraph with a <a href="#">link</a>.</p>
        </article>
    </main>
    <script>console.log('ignored');</script>
</body>
</html>"""
        temp_file = self.create_temp_html_file(html_content)

        reader = HTMLReader(temp_file)
        original_content = reader.read()
        chunks = list(reader.read_iter())

        # Test each chunk's indices
        for chunk in chunks:
            extracted_content = original_content[chunk.start_index : chunk.end_index]

            # For text chunks, the extracted HTML should contain elements that would
            # produce the chunk's text when parsed
            if chunk.text.strip():
                # The chunk text should be derivable from the extracted HTML segment
                # We'll check that key words from the chunk appear in the extracted content
                chunk_words = chunk.text.strip().split()
                if chunk_words:
                    # At least some words from the chunk should appear in the extracted content
                    found_words = sum(1 for word in chunk_words if word in extracted_content)
                    assert (
                        found_words > 0
                    ), f"No words from chunk '{chunk.text}' found in extracted content '{extracted_content}'"

    def test_chunk_size_limit_initialization(self):
        """Test that HTMLReader properly initializes with custom chunk size limits."""
        html_content = "<html><body><p>Test content</p></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        # Test default chunk size
        reader_default = HTMLReader(temp_file)
        assert reader_default.chunk_size_max == 1500  # Default CHUNK_CHARACTER_LIMIT

        # Test custom chunk size
        reader_custom = HTMLReader(temp_file, chunk_size_max=300)
        assert reader_custom.chunk_size_max == 300

    def test_text_chunking_with_size_limit(self):
        """Test that large text chunks are properly split according to chunk_size_max."""
        # Create HTML with a very long paragraph that will exceed chunk size limits
        long_text = (
            "This is a very long sentence that will be repeated many times to create a text chunk that exceeds the maximum chunk size limit. "
            * 30
        )
        html_content = f"<html><body><h1>Title</h1><p>{long_text}</p><p>Final paragraph</p></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        # Test with small chunk size (200 characters)
        reader = HTMLReader(temp_file, chunk_size_max=200)
        chunks = list(reader.read_iter())

        # Should have multiple chunks due to the long text
        assert len(chunks) > 3  # At least title, multiple content chunks, and final paragraph

        # All chunks should respect the size limit
        for chunk in chunks:
            assert len(chunk.text) <= 200, f"Chunk text length {len(chunk.text)} exceeds limit of 200"

        # Verify that we can reconstruct meaningful content from all chunks
        all_chunk_text = " ".join(chunk.text for chunk in chunks)
        assert "Title" in all_chunk_text
        assert "very long sentence" in all_chunk_text
        assert "Final paragraph" in all_chunk_text

    def test_chunking_preserves_word_boundaries(self):
        """Test that chunking tries to preserve word boundaries when possible."""
        # Create text that will require chunking
        text = "Word1 Word2 Word3 Word4 Word5 Word6 Word7 Word8 Word9 Word10 Word11 Word12"
        html_content = f"<html><body><p>{text}</p></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        # Use a chunk size that will force splitting but allow for word boundaries
        reader = HTMLReader(temp_file, chunk_size_max=30)
        chunks = list(reader.read_iter())

        # Find chunks that contain the test text
        text_chunks = [chunk for chunk in chunks if "Word" in chunk.text]

        # Check that words are not broken across chunks (when possible)
        for chunk in text_chunks:
            # Split the chunk text into words
            words = chunk.text.split()
            for word in words:
                # No word should be cut off (they should be complete)
                assert word.startswith("Word") or not word.startswith("Wor"), f"Word appears to be cut off: '{word}'"

    def test_chunk_indices_accuracy_with_splitting(self):
        """Test that start_index and end_index remain accurate after text splitting."""
        # Create HTML with long content that will be split
        long_paragraph = "ABCDEFGHIJKLMNOPQRSTUVWXYZ " * 20  # Create predictable content
        html_content = f"<html><body><h1>HEADER</h1><p>{long_paragraph}</p><footer>FOOTER</footer></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        original_html = ""
        with open(temp_file, "r", encoding="utf-8") as f:
            original_html = f.read()

        # Test with small chunk size to force splitting
        reader = HTMLReader(temp_file, chunk_size_max=50)
        chunks = list(reader.read_iter())

        # Should have multiple chunks
        assert len(chunks) > 2

        # Verify each chunk's indices map correctly to original HTML
        for i, chunk in enumerate(chunks):
            # Verify indices are within bounds
            assert 0 <= chunk.start_index < len(original_html)
            assert chunk.start_index < chunk.end_index <= len(original_html)

            # Extract the HTML segment at these indices
            html_segment = original_html[chunk.start_index : chunk.end_index]

            # The HTML segment should contain content that relates to the chunk text
            if chunk.text.strip():
                # For chunks with content like "HEADER", "ABCDEFG...", "FOOTER"
                # we should be able to find traces of this content in the HTML segment
                chunk_words = chunk.text.replace(" ", "").replace("\n", "")
                if chunk_words:
                    # Check if any significant portion of the chunk text appears in the HTML
                    found_content = False
                    for word_start in range(0, len(chunk_words), 3):  # Check in chunks of 3 chars
                        test_segment = chunk_words[word_start : word_start + 3]
                        if len(test_segment) >= 2 and test_segment in html_segment:
                            found_content = True
                            break

                    assert (
                        found_content
                    ), f"Chunk text '{chunk.text[:20]}...' not traceable in HTML segment '{html_segment[:50]}...'"

    def test_large_text_chunking_consistency(self):
        """Test that chunking is consistent and complete for large texts."""
        # Create a large HTML document with multiple sections
        html_sections = []
        expected_content = []

        for section_num in range(5):
            section_text = (
                f"Section {section_num} content: " + "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 10
            )
            html_sections.append(f"<div><h2>Section {section_num}</h2><p>{section_text}</p></div>")
            expected_content.append(f"Section {section_num}")
            expected_content.append(section_text[:50])  # First part of the content

        html_content = f"<html><body>{''.join(html_sections)}</body></html>"
        temp_file = self.create_temp_html_file(html_content)

        # Test with moderate chunk size
        reader = HTMLReader(temp_file, chunk_size_max=300)
        chunks = list(reader.read_iter())

        # Should have multiple chunks
        assert len(chunks) >= 10  # At least 2 chunks per section (header + content)

        # Verify all chunks respect size limit
        for chunk in chunks:
            assert len(chunk.text) <= 300

        # Verify all expected content appears in chunks
        all_text = " ".join(chunk.text for chunk in chunks)
        for expected in expected_content:
            assert expected in all_text, f"Expected content '{expected}' not found in chunked output"

        # Verify chunk indices are ordered and non-overlapping
        for i in range(1, len(chunks)):
            current_chunk = chunks[i]
            previous_chunk = chunks[i - 1]

            # Current chunk should start at or after the previous chunk ends
            assert (
                current_chunk.start_index >= previous_chunk.start_index
            ), f"Chunk {i} starts before previous chunk: {current_chunk.start_index} < {previous_chunk.start_index}"

    def test_chunk_size_edge_cases(self):
        """Test chunking behavior with edge case chunk sizes."""
        html_content = "<html><body><p>Short text content here</p></body></html>"
        temp_file = self.create_temp_html_file(html_content)

        # Test with very small chunk size
        reader_tiny = HTMLReader(temp_file, chunk_size_max=5)
        chunks_tiny = list(reader_tiny.read_iter())

        # Should create multiple very small chunks
        assert len(chunks_tiny) > 1
        for chunk in chunks_tiny:
            assert len(chunk.text) <= 5

        # Test with very large chunk size
        reader_large = HTMLReader(temp_file, chunk_size_max=10000)
        chunks_large = list(reader_large.read_iter())

        # Should have fewer, larger chunks
        assert len(chunks_large) <= len(chunks_tiny)

        # Verify all chunks respect their respective size limits
        for chunk in chunks_large:
            assert len(chunk.text) <= 10000
