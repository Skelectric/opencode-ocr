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
# Direct backend execution
uv run --directory ~/.config/opencode/tool pdf_ocr_backend.py <pdf_path> <output_format>

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

The tool connects to llama-swap at `http://localhost:8080/v1` using the `deepseek-ocr` model.

For remote systems (miniPC, DESKTOP-V4ETCL4), ensure `llmrig` is resolvable in `/etc/hosts`:
```
192.168.104.222 llmrig
```

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
