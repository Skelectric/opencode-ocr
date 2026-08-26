# PDF OCR Tool

An OCR tool for processing PDF files. Converts PDFs to high-quality images, performs OCR on each page, and returns markdown or plain text output. Supports both dedicated OCR models and multimodal vision models. Usable from both **OpenCode** and **pi**.

## Installation

The `deploy-tool.sh` script deploys to either or both harnesses:

- **OpenCode** tool → `~/.config/opencode/tool/` (`pdf-ocr.ts` + backend)
- **pi** extension → `~/.pi/agent/extensions/pdf-ocr/` + `~/.config/pi/tool/` (backend)

Each harness owns its own `.env` and `ocr_routing.json`; nothing is shared at runtime. Use `--target` to deploy to only one harness (useful if you don't have the other installed):

```bash
./deploy-tool.sh --target opencode   # OpenCode only
./deploy-tool.sh --target pi         # pi only
./deploy-tool.sh --target both       # both (default)
```

### OpenCode

This tool should be installed globally at `~/.config/opencode/tool/`.

### Automated Installation/Update (Recommended)

Use the provided deployment script for one-command installation and updates:

```bash
# Initial installation (OpenCode + pi)
./deploy-tool.sh

# Update after making changes to the repository
./deploy-tool.sh

# Force reinstallation (even if already installed)
./deploy-tool.sh --force

# Deploy to only one harness (skip the other)
./deploy-tool.sh --target opencode
./deploy-tool.sh --target pi

# Specify custom repository path
./deploy-tool.sh --repo /path/to/opencode-ocr
```

The script automatically detects if the tool is already installed and performs an update instead. After deploying the pi extension, run `/reload` in pi to load the `pdf_ocr` tool.

### pi

`./deploy-tool.sh --target pi` deploys only the pi extension and its backend (use `--target both` or omit `--target` to also deploy to OpenCode). The pi backend lives at `~/.config/pi/tool/` (override with the `PDF_OCR_TOOL_DIR` env var), and the extension at `~/.pi/agent/extensions/pdf-ocr/`. After deploying, run `/reload` in pi. See `pdf-ocr/pi/README.md` for pi-specific details.

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
  "_comment": "OCR Routing Configuration - Maps loaded model sets to preferred OCR method. Single-model keys work as before. Comma-separated keys match ALL loaded models (order-independent).",
  "_routing_options": {
    "deepseek-ocr": "Use DeepSeek-OCR model",
    "deepseek-ocr-2": "Use DeepSeek-OCR-2 model",
    "glm-ocr": "Use GLM-OCR model",
    "current_model": "Use the currently loaded model (requires vision support)"
  },
  "ocr_routing": {
    "_comment": "Model-set examples: comma-separated keys match ALL loaded models",
    "primary-model,secondary-model-a": "deepseek-ocr-2",
    "primary-model,secondary-model-b": "glm-ocr",
    "primary-model": "current_model"
  },
  "default": "current_model"
}
```

**Routing Options**:
- `deepseek-ocr`: Use the dedicated DeepSeek-OCR model for OCR tasks
- `deepseek-ocr-2`: Use the DeepSeek-OCR-2 model (improved accuracy)
- `glm-ocr`: Use the GLM-OCR model
- `current_model`: Use the currently loaded model (requires vision/multimodal support)

**Matching Logic** (most specific first):
1. **Exact model-set match**: Comma-separated key matches all loaded models exactly (order-independent)
2. **Single-model match**: Full model ID or partial match in `ocr_routing`
3. **Default**: Falls back to `default` value if no match found

**Single-Model Keys** (backward compatible):
Keys without commas work exactly as before:
```json
{
  "ocr_routing": {
    "primary-model": "deepseek-ocr-2",
    "another-model": "glm-ocr"
  },
  "default": "current_model"
}
```

**Model-Set Keys**:
When multiple models are loaded simultaneously, you can route based on the complete set:
```json
{
  "ocr_routing": {
    "primary-model,secondary-model-a": "deepseek-ocr-2",
    "primary-model,secondary-model-b": "glm-ocr",
    "primary-model": "current_model"
  },
  "default": "current_model"
}
```
In this example:
- When `primary-model` + `secondary-model-a` are loaded → uses `deepseek-ocr-2`
- When `primary-model` + `secondary-model-b` are loaded → uses `glm-ocr`
- When only `primary-model` is loaded → uses `current_model` (vision check required)

Always use current model (disable dedicated OCR):
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

For more examples, see `ocr_routing.json.example` in the repository.

## Technical Details

- PDF-to-image conversion at 144 DPI (high quality for OCR)
- PNG format with RGB color space
- Sequential page processing for memory management
- OCR parameters: temperature=0.0, max_tokens=8192, ngram_size=30, window_size=90

## Exit Codes

| Exit Code | Meaning | Scenario |
|-----------|---------|----------|
| **0** | Success | OCR completed successfully using either a dedicated OCR model or a multimodal model |
| **1** | General Error | File not found, API error, processing error, or OCR model failure |
| **3** | NO_OCR_SUPPORT | Current model is configured to use `current_model` routing but lacks vision/multimodal support |

## Troubleshooting

### Exit Code 3: NO_OCR_SUPPORT

This error occurs when:
- The current model is configured to use `current_model` for OCR routing
- The model does not support multimodal/vision capabilities

**Solution**: Add a routing rule for the loaded model(s) to `ocr_routing.json`:

For a single model:
```json
{
  "ocr_routing": {
    "your-model-name": "deepseek-ocr-2"
  },
  "default": "current_model"
}
```

For a model set (when multiple models are loaded):
```json
{
  "ocr_routing": {
    "your-model,secondary-model": "glm-ocr"
  },
  "default": "current_model"
}
```

Or switch to a model with vision support.

### OCR Model Failures (Exit Code 1)

If a dedicated OCR model is configured but fails:
- Verify the endpoint is running and accessible
- Check that the OCR model is loaded at the endpoint
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
