# DeepSeek-OCR PDF Tool

An OpenCode tool for processing PDF files using DeepSeek-OCR. Converts PDFs to high-quality images, performs OCR on each page, and returns markdown or plain text output.

## Installation

This tool should be installed globally at `~/.config/opencode/tool/`.

### Automated Installation/Update (Recommended)

Use the provided deployment script for one-command installation and updates:

```bash
# Initial installation
./deploy-tool.sh

# Update after making changes to the repository
./deploy-tool.sh

# Force reinstallation (even if already installed)
./deploy-tool.sh --force

# Specify custom repository path
./deploy-tool.sh --repo /path/to/opencode-ocr
```

The script automatically detects if the tool is already installed and performs an update instead.

### Manual Installation

```bash
# Create tool directory
mkdir -p ~/.config/opencode/tool/

# Copy files
cp pdf-ocr.ts ~/.config/opencode/tool/
cp pdf_ocr_backend.py ~/.config/opencode/tool/
cp pyproject.toml ~/.config/opencode/tool/

# Install Python dependencies
cd ~/.config/opencode/tool && uv sync
```

## Usage

**Important**: Python scripts must be run using `uv run` to ensure proper dependency management:

```bash
# Direct backend execution (with .env file)
uv run --directory ~/.config/opencode/tool --env-file .env pdf_ocr_backend.py <pdf_path> <output_format>

# Via OpenCode agent
Agent will use the pdf-ocr tool automatically
```

## Parameters

- `pdf_path`: Absolute path to PDF file
- `output_format`: Output format - "markdown" or "text" (defaults to "markdown")

## Dependencies

- openai>=1.0.0
- PyMuPDF>=1.23.0
- Pillow>=10.0.0

## Configuration

The tool connects to an OpenAI-compatible endpoint running DeepSeek-OCR. The endpoint can be configured in three ways:

1. **.env file** (recommended for persistent configuration):
   Copy `.env.example` to `.env` and edit it:
   ```bash
   cp .env.example .env
   # Edit .env with your endpoint URL
   ```
   Then run with `uv run --env-file .env`.

2. **Environment variable**:
   ```bash
   export DEEPSEEK_OCR_BASE_URL="http://your-endpoint:8080/v1"
   ```

3. **Command-line argument** (overrides both above):
   ```bash
   uv run --directory ~/.config/opencode/tool pdf_ocr_backend.py <pdf_path> <output_format> --base-url http://your-endpoint:8080/v1
   ```

If none of these are set, the tool will throw an error.

The tool uses the `deepseek-ocr` model name when making requests to the endpoint.

## Technical Details

- PDF-to-image conversion at 144 DPI (high quality for OCR)
- PNG format with RGB color space
- Sequential page processing for memory management
- OCR parameters: temperature=0.0, max_tokens=8192, ngram_size=30, window_size=90

## Future Enhancements

- Partial page range support (e.g., process pages 5-10 only)
- Progress reporting during OCR processing
- Batch processing of multiple PDFs
- Additional output formats (e.g., JSON, HTML)
- Image quality settings configuration
