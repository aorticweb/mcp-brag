# MCP-RAG

A high-performance Retrieval-Augmented Generation (RAG) system built with Model Context Protocol (MCP), providing semantic search and document embedding capabilities for AI applications.

## Overview

MCP-RAG is a comprehensive document processing and semantic search solution that enables AI systems to efficiently retrieve relevant information from large document collections. It combines powerful embedding generation, vector storage, and MCP server integration to create a seamless RAG experience.

### Key Features

- **Multi-format Document Support**: Process text, HTML, DOCX, PPTX, PDF files and more
- **Audio Transcription**: Automatic transcription of audio files (MP3, WAV, etc.) and YouTube videos
- **Semantic Search**: Advanced vector-based search with configurable parameters
- **MCP Integration**: Built-in Model Context Protocol server for seamless AI integration
- **Real-time Processing**: Asynchronous document processing with progress tracking
- **Electron UI**: Cross-platform desktop application for easy management
- **REST API**: Comprehensive HTTP API for programmatic access

## Supported File Types

| File Type | Extension | Description | Status |
|-----------|-----------|-------------|---------|
| Text | `.txt` | Plain text files | ✅ Tested |
| HTML | `.html` | HyperText Markup Language files | ✅ Tested |
| DOCX | `.docx` | Microsoft Word documents | ✅ Tested |
| PPTX | `.pptx` | Microsoft PowerPoint presentations | 🔄 In Progress |
| PDF | `.pdf` | Portable Document Format files | ✅ Tested |
| Audio | `.mp3`, `.wav`, `.m4a` | Audio files (transcribed to text) | ✅ Tested |
| YouTube | `.mp3` | YouTube videos (transcribed to text) | ✅ Tested |
| Other | Various | Any other text format files | ✅ Tested |

## Architecture

MCP-RAG consists of three main components:

1. **Embedder Service**: Processes documents and generates vector embeddings
2. **MCP Server**: Provides MCP protocol interface and REST API endpoints
3. **Electron UI**: Desktop application for managing documents and search

## Installation

### Prerequisites

- Python 3.12.9 or higher
- Node.js 22.9.0 or higher
- uv (Python package manager) - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`
- macOS, Linux, or Windows

### Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mcp-rag.git
cd mcp-rag
```

2. Install all dependencies using uv:
```bash
make install
# Or manually:
uv sync --extra server --extra embedder --extra dev
```

3. Install UI dependencies:
```bash
cd ui
npm install
cd ..
```

4. Run the services:
```bash
# Using make commands:
# Terminal 1: Start the MCP server (includes embedder)
make run-server

# Terminal 2: Start the UI (development mode)  
make run-ui-app-dev

# Or manually with uv:
# Terminal 1: Start the embedder
uv run python -m embedder.main

# Terminal 2: Start the MCP server
uv run python -m server.main

# Terminal 3: Start the UI (development mode)
cd ui && npm run dev
```

## Configuration

The system can be configured through environment variables or the API. Key configuration options include:

### Editable Settings
- `INGESTION_PROCESS_MAX_FILE_PATHS`: Maximum files per batch
- `CHUNK_CHARACTER_LIMIT`: Character limit for text chunks
- `SEARCH_RESULT_LIMIT`: Maximum search results
- `SEARCH_PROCESSING_TIMEOUT_SECONDS`: Search timeout

### System Settings (Read-only)
- `VECTORIZER_MODEL_PATH`: Path to the embedding model
- `EMBEDDING_SIZE`: Dimension of embeddings (default: 384)
- `SQLITE_DB_LOCATION`: Database location

## API Documentation

The system provides a comprehensive REST API for all operations. Full API documentation is available in [docs/openapi.yaml](docs/openapi.yaml).

### Key Endpoints

- `POST /manual/process_file_async`: Process documents for embedding
- `POST /manual/search_file`: Semantic search across documents
- `GET /manual/data_sources`: List available data sources
- `POST /manual/process_url_async`: Process URLs (YouTube, etc.)
- `GET /manual/config`: Get/set configuration

## MCP Integration

MCP-RAG implements the Model Context Protocol, allowing seamless integration with AI assistants. The server name is "Corpus" and provides tools for document search and retrieval.

## Development

### Project Structure

```
mcp-rag/
├── embedder/          # Document processing and embedding generation
├── server/            # MCP server and API implementation
├── transcriber/       # Audio transcription services
├── ui/                # Electron desktop application
├── tests/             # Test suite
└── docs/              # Documentation
```

### Running Tests

```bash
make unit-test
# Or manually:
uv run pytest tests/
```

### Building the Desktop App

```bash
# Build complete application (server + UI)
make build

# Or build components separately:
make build-server  # Build server executable
make package-app   # Build desktop app

# Manual commands:
cd ui
npm run package  # Package for current platform
npm run make     # Create distributable
```

### Development Commands

```bash
# Format code
make format

# Lint code
make lint

# Update dependencies
make update

# Clean and reinstall
make clean

# See all available commands
make help
```

## Performance

- Supports processing of large document collections
- Efficient vector storage using SQLite with vector extensions
- Configurable batch processing for optimal throughput
- Multi-threaded architecture for concurrent operations

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## Third-Party Licenses

This project includes icon components from the [Goose](https://github.com/block/goose) project, licensed under the Apache License 2.0. See the individual icon files in `ui/src/components/icons/` for license headers.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions, issues, or feature requests, please open an issue on the GitHub repository.

## Vibe
The entire ui was vibe coded using Claude code.
Some of the python features were also vibe coded at times (especially test generation).
