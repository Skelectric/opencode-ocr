# DeepSeek-OCR PDF Tool Implementation Plan

## Executive Summary

This plan outlines the creation of a global OpenCode tool for processing PDF files using DeepSeek-OCR. The tool converts PDFs to high-quality images, performs OCR on each page, and returns markdown or plain text output, deployed across all OpenCode instances (llmrig, miniPC, DESKTOP-V4ETCL4).

## Design Decisions

Based on requirements analysis:
1. **Tool Location**: Global installation (`~/.config/opencode/tool/`)
2. **Page Processing**: Full PDF processing only (no partial page ranges initially)
3. **Output Format**: Markdown or plain text
4. **Error Handling**: Fail-fast on any errors
5. **Progress Reporting**: Wait until complete before returning results
6. **Tool Description Injection**: Self-contained in tool definition (no AGENTS.md modifications needed)
7. **PDF Conversion**: PDF-to-image conversion using PyMuPDF at 144 DPI before OCR processing

---

## Phase 1: Create Tool in Repository

### 1.1 Tool Structure

**Development Location**: `~/opencode-ocr/pdf-ocr/tool/pdf-ocr.ts`

**Backend Script**: `~/opencode-ocr/pdf-ocr/tool/pdf_ocr_backend.py`

**Python Dependencies**: `~/opencode-ocr/pdf-ocr/pyproject.toml`

**Deployment Target**: `~/.config/opencode/tool/` (when ready for testing)

### 1.2 Tool Definition (`pdf-ocr.ts`)

```typescript
import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "Extract text from PDF files using DeepSeek-OCR. Processes entire PDFs and returns markdown or plain text output. Use this when you need to transcribe PDF documents for analysis or processing.",
  args: {
    pdf_path: tool.schema.string().describe("Absolute path to PDF file"),
    output_format: tool.schema.string().describe("Output format: 'markdown' or 'text' (defaults to 'markdown')")
  },
  async execute(args) {
    const result = await Bun.$`uv run --directory ~/opencode-ocr/pdf-ocr pdf_ocr_backend.py ${args.pdf_path} ${args.output_format || 'markdown'}`.text()
    return result.trim()
  }
})
```

**Note**: When deploying to `~/.config/opencode/tool/`, update the path to match deployment location.

### 1.3 Python Backend Implementation (`pdf_ocr_backend.py`)

**Key Features**:
- PDF to image conversion using PyMuPDF (fitz) at 144 DPI
- OCR processing via OpenAI client to llama-swap endpoint
- Full PDF processing (all pages)
- Sequential page processing to manage memory
- Temporary image cleanup after OCR
- Fail-fast error handling
- Markdown or plain text output
- No progress reporting (waits until complete)

**PDF Conversion Workflow**:
1. Open PDF document using PyMuPDF (fitz)
2. For each page:
   - Convert page to PNG image at 144 DPI (high quality)
   - Ensure RGB color space (required by DeepSeek-OCR model)
   - Save image to temporary file or memory buffer
   - Send image to DeepSeek-OCR for text extraction
   - Append OCR result to output with page markers
   - Clean up temporary image data
3. Return combined output from all pages

**Dependencies** (managed via `pyproject.toml`):
- `openai` (OpenAI API client)
- `PyMuPDF` (fitz) for PDF handling
- `Pillow` (PIL) for image processing

**API Configuration**:
```python
from openai import OpenAI

client = OpenAI(
    api_key="EMPTY",
    base_url="http://localhost:8080/v1",
    timeout=3600
)

response = client.chat.completions.create(
    model="deepseek-ocr",
    messages=[...],  # Image + "Free OCR." prompt
    max_tokens=8192,
    temperature=0.0,
    extra_body={
        "skip_special_tokens": False,
        "vllm_xargs": {
            "ngram_size": 30,
            "window_size": 90,
            "whitelist_token_ids": [128821, 128822],
        },
    },
)
```

### 1.4 Python Dependencies (`pyproject.toml`)

```toml
[project]
name = "pdf-ocr-tool"
version = "0.1.0"
description = "DeepSeek-OCR PDF processing backend for OpenCode"
requires-python = ">=3.10"
dependencies = [
    "openai>=1.0.0",
    "PyMuPDF>=1.23.0",
    "Pillow>=10.0.0",
]

[project.scripts]
pdf_ocr_backend = "pdf_ocr_backend:main"
```

**Usage**: Run Python scripts using `uv run`:
```bash
uv run --directory ~/opencode-ocr/pdf-ocr pdf_ocr_backend.py <pdf_path> <output_format>
```

**Processing Flow**:
1. Validate PDF file exists and is readable
2. Open PDF document using PyMuPDF
3. For each page in PDF:
   - Convert page to PNG image at 144 DPI (high quality for OCR)
   - Ensure RGB color space (model requirement)
   - Encode image as base64 data URL
   - Send to DeepSeek-OCR with "Free OCR." prompt
   - Extract and format OCR response
   - Clean up image data
4. Combine all page results with page break markers
5. Return complete output or fail on first error

### 1.5 Error Handling Strategy

**Fail-Fast Scenarios**:
- PDF file not found or inaccessible
- Corrupt or invalid PDF format
- OCR service unavailable or timeout
- API errors from llama-swap
- Image processing failures

**Error Messages**: Clear, descriptive errors indicating failure point

---

## Phase 2: Testing & Validation

### 2.0 Deployment for Testing

Before testing, deploy the tool from the repository to the live directory:

```bash
# Create deployment directory
mkdir -p ~/.config/opencode/tool/

# Copy tool files
cp ~/opencode-ocr/pdf-ocr/tool/pdf-ocr.ts ~/.config/opencode/tool/
cp ~/opencode-ocr/pdf-ocr/tool/pdf_ocr_backend.py ~/.config/opencode/tool/
cp ~/opencode-ocr/pdf-ocr/pyproject.toml ~/.config/opencode/tool/

# Update execute path in pdf-ocr.ts to use deployment location
# (or use relative path if uv run handles this correctly)
```

**Testing Commands**:
- Run backend directly: `uv run --directory ~/.config/opencode/tool pdf_ocr_backend.py <pdf_path> <output_format>`
- Test via OpenCode: Use the pdf-ocr tool through the agent interface

### 2.2 Test Cases

1. **Simple single-page PDF**
   - Basic text extraction
   - Verify markdown formatting
   - Confirm no errors

2. **Multi-page document**
   - Page concatenation
   - Page break markers
   - Consistent formatting across pages

3. **Complex layout** (bank statement template)
   - Table extraction
   - Column preservation
   - Numeric data accuracy

4. **Large PDF (>10 pages)**
   - Memory management
   - Processing time benchmarking
   - Complete output verification

5. **Error scenarios**
   - Missing file handling
   - Corrupt PDF detection
   - Network timeout handling

### 2.3 Performance Metrics

- Processing time per page
- Total processing time for multi-page PDFs
- Memory usage (VRAM monitoring)
- OCR accuracy verification

### 2.4 Test Environment

**Primary Testing**: llmrig (localhost:8080)
- Direct llama-swap access
- GPU acceleration available
- Reference test files from `~/deepseek-ocr-testing/`

---

## Phase 3: Multi-System Deployment

### 3.1 Deployment Strategy

**Development Workflow**:
1. Create and modify files in `~/opencode-ocr/pdf-ocr/`
2. Test locally using `uv run`
3. Deploy to `~/.config/opencode/tool/` when ready for testing
4. Verify functionality with test PDFs

**Global Tool Installation** on all systems:
- Location: `~/.config/opencode/tool/pdf-ocr.ts`
- Single maintenance point (repository)
- Available across all projects

### 3.2 System-Specific Configuration

#### llmrig (Primary OCR Server)
- **llama-swap endpoint**: `http://localhost:8080/v1`
- **Model**: `deepseek-ocr` alias → `unsloth/DeepSeek-OCR`
- **Advantage**: Direct access, GPU acceleration, lowest latency

#### miniPC (Secondary)
- **llama-swap endpoint**: `http://llmrig:8080/v1` (network access)
- **Requirements**: Network connectivity to llmrig
- **Latency**: Higher than local but acceptable

#### DESKTOP-V4ETCL4 (Secondary)
- **llama-swap endpoint**: `http://llmrig:8080/v1` (network access)
- **Requirements**: Network connectivity to llmrig
- **Latency**: Higher than local but acceptable

### 3.3 Network Configuration

**Hosts File** (ensure llmrig is resolvable):
```bash
# /etc/hosts on miniPC and DESKTOP-V4ETCL4
192.168.104.222 llmrig
```

**Firewall Rules** (llmrig):
- Allow port 8080 from miniPC and DESKTOP-V4ETCL4
- Current configuration should already permit this

### 3.4 Installation Steps

For each system (llmrig, miniPC, DESKTOP-V4ETCL4):

1. Create tool directory: `mkdir -p ~/.config/opencode/tool/`
2. Copy `pdf-ocr.ts` to `~/.config/opencode/tool/`
3. Copy `pdf_ocr_backend.py` to `~/.config/opencode/tool/`
4. Copy `pyproject.toml` to `~/.config/opencode/tool/`
5. Install Python dependencies: `cd ~/.config/opencode/tool && uv sync`
6. Verify tool is available: `opencode tools` (should show pdf-ocr)

**Note**: All Python functionality should be run using `uv run`:
```bash
uv run --directory ~/.config/opencode/tool pdf_ocr_backend.py <pdf_path> <output_format>
```

---

## Phase 4: Documentation & Maintenance

### 4.1 Tool Description

The tool's functionality is self-documenting through its description field:
- "Extract text from PDF files using DeepSeek-OCR. Processes entire PDFs and returns markdown or plain text output. Use this when you need to transcribe PDF documents for analysis or processing."

**No AGENTS.md modifications needed** - tool descriptions are automatically injected into the system prompt.

### 4.2 Usage Examples

**Basic Usage**:
```
User: "Can you transcribe this PDF to markdown?"
[User provides PDF path]
Agent: Uses pdf-ocr tool with pdf_path and output_format="markdown"
```

**Plain Text Output**:
```
User: "Extract plain text from this PDF"
[User provides PDF path]
Agent: Uses pdf-ocr tool with pdf_path and output_format="text"
```

### 4.3 Maintenance Considerations

- Monitor llama-swap service availability
- Track OCR accuracy for different document types
- Update dependencies in `pyproject.toml` and run `uv sync`
- Consider adding partial page range support in future versions
- Always test changes in `~/opencode-ocr/pdf-ocr/` before deploying

---

## Technical Specifications

### API Configuration

**Base URL**: `http://localhost:8080/v1` (llmrig)
**Model**: `deepseek-ocr` (alias for `unsloth/DeepSeek-OCR`)
**Timeout**: 3600 seconds (1 hour for large PDFs)

**OCR Parameters**:
- `temperature=0.0` (deterministic output)
- `max_tokens=8192` (sufficient for complex pages)
- `ngram_size=30`, `window_size=90` (DeepSeek-OCR optimized settings)
- `whitelist_token_ids=[128821, 128822]` (table cell tokens)

### Image Processing

**DPI**: 144 (high quality for OCR)
**Format**: PNG (lossless compression)
**Color Space**: RGB (required by model)
**Memory Management**: Sequential page processing to avoid OOM
**Cleanup**: Temporary images deleted after OCR processing

### Output Format

**Markdown**:
- Document structure preserved
- Tables in markdown format
- Page break markers between pages
- Images extracted where detected

**Plain Text**:
- Text content only
- Minimal formatting
- Page break markers between pages

---

## Success Criteria

### Functional Requirements
- ✅ Tool successfully processes PDF files
- ✅ Returns markdown or plain text output
- ✅ Handles multi-page documents
- ✅ Fail-fast error handling
- ✅ Works on all three systems

### Performance Requirements
- ✅ Processing time < 30 seconds per page
- ✅ Memory usage stable (no leaks)
- ✅ Network latency acceptable on remote systems

### Quality Requirements
- ✅ OCR accuracy > 95% on test documents
- ✅ Table structure preserved
- ✅ No data loss or corruption

---

## References

### OpenCode Documentation
- [Custom Tools](https://opencode.ai/docs/custom-tools/)
- [Tools](https://opencode.ai/docs/tools/)
- [Agents](https://opencode.ai/docs/agents/)

### DeepSeek-OCR Integration
- Test scripts: `~/deepseek-ocr-testing/test_llamaswap_ocr.py`
- PDF processing: `~/deepseek-ocr-testing/run_dpsk_ocr_pdf.py`
- Model: `unsloth/DeepSeek-OCR`

### System Configuration
- llama-swap config: `~/.config/llama-swap/config.yaml`
- System knowledge: `/home/philkir/llmrig-devops/system-knowledge/`

---

## Appendix A: Sample Code Structure

### Python Backend Skeleton

```python
#!/usr/bin/env python3
import sys
import fitz  # PyMuPDF
import io
import base64
from openai import OpenAI
from pathlib import Path

def main():
    pdf_path = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else 'markdown'

    # Validate PDF exists
    if not Path(pdf_path).exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    # Initialize OCR client
    client = OpenAI(
        api_key="EMPTY",
        base_url="http://localhost:8080/v1",
        timeout=3600
    )

    # Process PDF
    try:
        doc = fitz.open(pdf_path)
        results = []

        for page_num in range(doc.page_count):
            page = doc[page_num]

            # Convert page to image at 144 DPI
            pix = page.get_pixmap(dpi=144)
            img_bytes = pix.tobytes("png")

            # Encode as base64 for API
            img_base64 = base64.b64encode(img_bytes).decode()
            image_url = f"data:image/png;base64,{img_base64}"

            # Process with OCR
            response = client.chat.completions.create(
                model="deepseek-ocr",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": "Free OCR."}
                    ]
                }],
                max_tokens=8192,
                temperature=0.0,
                extra_body={
                    "skip_special_tokens": False,
                    "vllm_xargs": {
                        "ngram_size": 30,
                        "window_size": 90,
                        "whitelist_token_ids": [128821, 128822]
                    }
                }
            )

            results.append(f"--- Page {page_num + 1} ---\n{response.choices[0].message.content}")

        output = "\n\n".join(results)
        print(output)
        doc.close()

    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Directory Structure

```
~/opencode-ocr/
└── pdf-ocr/
    ├── pyproject.toml          # Python dependencies
    └── tool/
        ├── pdf-ocr.ts          # TypeScript tool definition
        └── pdf_ocr_backend.py  # Python OCR backend
```

---

**Document Version**: 1.0
**Created**: January 12, 2026
**Status**: Ready for Implementation
