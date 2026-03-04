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

### Endpoint Configuration

The tool connects to an OpenAI-compatible endpoint. The endpoint can be configured in three ways:

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

### OCR Routing Configuration

The tool uses model-based routing to determine which OCR method to use. This is configured in `ocr_routing.json`:

**Location**: `~/.config/opencode/tool/pdf-ocr/tool/ocr_routing.json`

**Structure**:
```json
{
  "_comment": "OCR Routing Configuration - Maps model IDs to preferred OCR method",
  "_routing_options": {
    "deepseek-ocr": "Use DeepSeek-OCR model (requires sufficient VRAM)",
    "current_model": "Use the currently loaded model (requires vision support)"
  },
  "ocr_routing": {
    "kimi-k2.5": "deepseek-ocr",
    "kimi-k2.5-abliterated": "deepseek-ocr"
  },
  "default": "current_model"
}
```

**Routing Options**:
- `deepseek-ocr`: Use the dedicated DeepSeek-OCR model for OCR tasks
- `current_model`: Use the currently loaded model (requires vision/multimodal support)

**Matching Logic**:
1. Exact match: Full model ID in `ocr_routing`
2. Partial match: Pattern appears in model ID or model ID appears in pattern
3. Default: Falls back to `default` value if no match found

**Examples**:

Enable DeepSeek-OCR for Kimi models:
```json
{
  "ocr_routing": {
    "kimi-k2.5": "deepseek-ocr",
    "kimi-k2.5-abliterated": "deepseek-ocr"
  },
  "default": "current_model"
}
```

Always use current model (disable DeepSeek-OCR):
```json
{
  "ocr_routing": {},
  "default": "current_model"
}
```

Enable DeepSeek-OCR for all models by default:
```json
{
  "ocr_routing": {},
  "default": "deepseek-ocr"
}
```

## Technical Details

- PDF-to-image conversion at 144 DPI (high quality for OCR)
- PNG format with RGB color space
- Sequential page processing for memory management
- OCR parameters: temperature=0.0, max_tokens=8192, ngram_size=30, window_size=90

## Exit Codes

| Exit Code | Meaning | Scenario |
|-----------|---------|----------|
| **0** | Success | OCR completed successfully using either DeepSeek-OCR or a multimodal model |
| **1** | General Error | File not found, API error, processing error, or DeepSeek-OCR failure |
| **3** | NO_OCR_SUPPORT | Current model is configured to use `current_model` routing but lacks vision/multimodal support |

## Troubleshooting

### Exit Code 3: NO_OCR_SUPPORT

This error occurs when:
- The current model is configured to use `current_model` for OCR routing
- The model does not support multimodal/vision capabilities

**Solution**: Add the model to `ocr_routing.json` with `deepseek-ocr` value:
```json
{
  "ocr_routing": {
    "your-model-name": "deepseek-ocr"
  },
  "default": "current_model"
}
```

Or switch to a model with vision support.

### DeepSeek-OCR Failures (Exit Code 1)

If DeepSeek-OCR is configured but fails:
- Verify the endpoint is running and accessible
- Check that the DeepSeek-OCR model is loaded
- Review endpoint logs for errors

### Configuration File Not Found

If `ocr_routing.json` is missing, the tool will use defaults (`current_model`). To create the configuration file, run:
```bash
./deploy-tool.sh
```

## Future Enhancements

- Partial page range support (e.g., process pages 5-10 only)
- Progress reporting during OCR processing
- Batch processing of multiple PDFs
- Additional output formats (e.g., JSON, HTML)
- Image quality settings configuration
