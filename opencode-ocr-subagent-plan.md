# OpenCode OCR Subagent - Feasibility & Implementation Plan

## Executive Summary

OCR subagent development is **in progress** with DeepSeek-OCR successfully integrated into llama-swap. vLLM backend operational alongside GLM-4.7 with concurrent operation validated (94% VRAM utilization). Next phase: subagent implementation and testing.

## Current State

**Infrastructure**: OpenCode (miniPC) → SSH → llama-swap (llmrig:8080) → ik_llama.cpp → GPU models

**Model Roles**:
- **GLM-4.7** (main agent model, 200K context, UD-Q4_K_XL quantization)
- **DeepSeek-OCR** (✅ integrated via vLLM, llama-swap proxy operational)

## Architectural Design

### Subagent Communication Flow
```
OpenCode (main agent using GLM-4.7)
    ↓ Task delegation (Task tool with subagent_type)
    └─→ OCR Subagent (DeepSeek-OCR) → PDF transcription
         ↓
    Returns structured text response to main agent (GLM-4.7)
```

### Subagent Capabilities
**OCR Subagent** (`pdf-ocr`):
- Long PDF transcription to markdown
- Document structure preservation
- Multi-page processing
- High-accuracy text extraction
- Table and layout recognition

## Implementation Phases

### Phase 1: DeepSeek-OCR Integration ✅ Complete

**Objective**: Deploy DeepSeek-OCR via vLLM backend alongside llama-swap for concurrent operation with optimized GLM-4.7

**Status**: ✅ Completed Dec 29, 2025 - Dec 31, 2025

**Completed Tasks**:
1. ✅ **Install vLLM** with DeepSeek-OCR support on llmrig
    - Python environment setup at `~/deepseek-ocr-testing/.venv`
    - vLLM 0.13.0 installation with OCR-specific dependencies
    - DeepSeek-OCR model downloaded (6.2GB from HuggingFace)

2. ✅ **Configure sidecar service** (extend llama-swap)
     - Added DeepSeek-OCR to llama-swap config.yaml:
       ```yaml
       models:
         deepseek-ocr:
           cmd: |
             source ~/deepseek-ocr-testing/.venv/bin/activate && \
             vllm serve unsloth/DeepSeek-OCR \
               --logits_processors vllm.model_executor.models.deepseek_ocr:NGramPerReqLogitsProcessor \
               --no-enable-prefix-caching \
               --mm-processor-cache-gb 0 \
               --allowed-local-media-path /home/philkir \
               --port ${PORT}
           useModelName: "unsloth/DeepSeek-OCR"
           aliases: ["ocr", "deepseek-ocr"]
           description: "DeepSeek-OCR model for PDF transcription"

       groups:
         ocr-group:
           swap: false
           exclusive: false
           members:
             - glm-4.7
             - deepseek-ocr
       ```
     - llama-swap automatically routes requests by model name
     - Concurrent GLM-4.7 + DeepSeek-OCR operation configured

3. ✅ **Test OCR API**:
    - Single image OCR validated with standard prompt "Free OCR."
    - PDF page extraction and processing tested
    - Ngram processor parameters verified (ngram_size=30, window_size=90)

4. ✅ **Performance benchmark**:
    - Actual: ~2 seconds for complex documents (bank statement)
    - Processing time: 34.79s for performance table via llama-swap proxy
    - Memory usage: ~15GB VRAM with gpu_memory_utilization=0.15

5. ✅ **Test concurrent GLM-4.7 + DeepSeek-OCR operation**:
    - VRAM usage: 92.25GB / 97.89GB (94% utilization)
    - DeepSeek-OCR: 15.46GB VRAM, GLM-4.7: 76.76GB VRAM
    - No unload conflicts or OOM errors
    - Parallel API requests validated
    - Stability confirmed under test load

**Success Criteria Achieved**: vLLM OCR endpoint operational with OpenAI-compatible API and stable concurrent operation with GLM-4.7

### Phase 2: OCR Subagent Implementation
*New phase*

**Objective**: Build and test PDF OCR subagent using DeepSeek-OCR

**Tasks**:
1. **Develop OCR subagent code**:
    - Create `pdf-ocr` subagent definition in `/home/ubuntu/.config/opencode/AGENTS.md`
    - Implement PDF preprocessing:
      - PDF page extraction (using PyPDF2 or pdf2image)
      - Convert pages to images for OCR
      - Handle multi-page documents
    - Implement chunked processing:
      - Process pages in batches (e.g., 10 pages at a time)
      - Combine results with markdown headers
      - Progress tracking for user feedback
    - Define markdown output format:
      - Preserve document structure (headings, paragraphs)
      - Table representation
      - Page break markers

2. **Test OCR workflows**:
    - "Transcribe this PDF to markdown"
    - "Extract text from pages 5-10 of this PDF"
    - "Summarize the contents of this document"

3. **Performance optimization**:
    - Batch processing for efficiency
    - Memory management for large documents (>100 pages)
    - Error recovery (failed page retries)
    - Caching for repeated documents

**Deliverables**: Working pdf-ocr subagent with 3 validated use cases

## Technical Specifications

### OCR Subagent API
```python
# Subagent call example
Task(
    subagent_type="pdf-ocr",
    prompt="Transcribe this PDF to markdown: /path/to/document.pdf",
    description="Extract text from PDF"
)

# Returns markdown-formatted text:
"""
# Document Title

## Section 1
Lorem ipsum dolor sit amet...

## Section 2
More text content...

Table:
| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
"""
```

### Main Agent Delegation Flow
```python
# Main agent (GLM-4.7) determines need for OCR
if user_request_contains_pdf():
    ocr_result = Task(
        subagent_type="pdf-ocr",
        prompt=f"Transcribe this PDF to markdown: {pdf_path}",
        description="Extract document content"
    )
    # GLM-4.7 synthesizes ocr_result into final response
    return generate_response_with_context(ocr_result)
```

## Resource Requirements

### Current Hardware (llmrig)
- **GPU**: NVIDIA RTX PRO 6000 Blackwell Workstation Edition (97,247 MiB VRAM)
- **RAM**: 768 GB DDR4
- **CPU**: 2x AMD Epyc 9355 (64 cores, 128 threads)
- **OS**: Ubuntu 24.04.3 LTS

## Dependencies

1. ✅ llama-swap operational on llmrig
2. ✅ GLM-4.7 model available and optimized (ubatch=16384, cache tuning)
3. ✅ DeepSeek-V3.1-Terminus available (backup)
4. ✅ vLLM 0.13.0 installed at `~/deepseek-ocr-testing/.venv`
5. ✅ DeepSeek-OCR model downloaded (unsloth/DeepSeek-OCR)
6. ✅ Concurrent GLM-4.7 + DeepSeek-OCR validated (92.25GB / 97.89GB VRAM)

## Next Immediate Steps

1. **Begin Phase 2**: OCR subagent development
    - Create `pdf-ocr` subagent definition in AGENTS.md
    - Implement PDF preprocessing (page extraction, image conversion)
    - Implement chunked processing for multi-page documents
    - Define markdown output format with structure preservation
    - Test with sample PDF documents

## Example End-to-End Workflows

### Workflow 1: PDF Document Analysis
```
User: "Can you summarize the key points from this research paper?"
[User uploads paper.pdf]

Main Agent (GLM-4.7):
1. Detects PDF attachment
2. Delegates to pdf-ocr subagent:
   Task(subagent_type="pdf-ocr",
        prompt="Transcribe this PDF to markdown: paper.pdf",
        description="Extract document content")

OCR Subagent (DeepSeek-OCR):
1. Extracts pages from PDF
2. Processes each page with OCR
3. Returns markdown-formatted text

Main Agent (GLM-4.7):
1. Receives markdown content
2. Analyzes and summarizes key points
3. Returns structured summary to user
```

### Workflow 2: Partial Document Extraction
```
User: "Extract text from pages 5-10 of this PDF"
[User uploads report.pdf]

Main Agent (GLM-4.7):
1. Detects PDF attachment with page range request
2. Delegates to pdf-ocr subagent:
   Task(subagent_type="pdf-ocr",
        prompt="Extract pages 5-10 from report.pdf as markdown",
        description="Extract partial document content")

OCR Subagent (DeepSeek-OCR):
1. Extracts specified pages from PDF
2. Processes each page with OCR
3. Returns markdown-formatted text for pages 5-10

Main Agent (GLM-4.7):
1. Receives markdown content
2. Provides extracted content to user
```

### Workflow 3: Document Summarization
```
User: "Summarize the contents of this document"
[User uploads manual.pdf]

Main Agent (GLM-4.7):
1. Detects PDF attachment with summary request
2. Delegates to pdf-ocr subagent:
   Task(subagent_type="pdf-ocr",
        prompt="Transcribe this entire PDF to markdown: manual.pdf",
        description="Extract complete document content")

OCR Subagent (DeepSeek-OCR):
1. Extracts all pages from PDF
2. Processes each page with OCR
3. Returns complete markdown-formatted text

Main Agent (GLM-4.7):
1. Receives complete markdown content
2. Analyzes and generates comprehensive summary
3. Returns structured summary to user
```

---

# Appendix A: DeepSeek-OCR Integration Details

## DeepSeek-OCR Requirements (from vLLM + Unsloth docs)

- **Model**: `unsloth/DeepSeek-OCR` (Unsloth's fine-tuned quant)
- **Backend**: vLLM (not llama.cpp)
- **vLLM Version**: ≥0.11.1 (current: 0.13.0 installed via `uv pip install vllm`)
- **Installation**: Using uv with venv at `~/.venv_vllm`
- **Core parameters**:
  - `--logits_processors vllm.model_executor.models.deepseek_ocr:NGramPerReqLogitsProcessor`
  - `--no-enable-prefix-caching`
  - `--mm-processor-cache-gb 0`
- **Recommended settings**:
  - `temperature=0.0`
  - `max_tokens=8192`
  - `ngram_size=30`
  - `window_size=90`
  - `whitelist_token_ids=[128821, 128822]` (for <td>, </td>)
- **Input**: Multimodal (image + text)
- **API**: OpenAI-compatible server

## Integration Strategy

### Extend llama-swap with vLLM Model
- Add DeepSeek-OCR model to llama-swap config.yaml using standard structure
- Use `cmd` to run vLLM server (no backend field needed)
- Leverage existing llama-swap routing infrastructure
- Supports groups for concurrent model management
- Leverages existing llama-swap routing infrastructure

## Key Integration Points

### Configuration Structure (extending config.yaml)
```yaml
models:
  deepseek-ocr:
    cmd: |
      source ~/.venv_vllm/bin/activate && \
      vllm serve unsloth/DeepSeek-OCR \
        --logits_processors vllm.model_executor.models.deepseek_ocr:NGramPerReqLogitsProcessor \
        --no-enable-prefix-caching \
        --mm-processor-cache-gb 0 \
        --port ${PORT}
    aliases: ["ocr", "deepseek-ocr"]
    description: "DeepSeek-OCR model for PDF transcription"

groups:
  ocr-group:
    swap: false
    exclusive: false
    members:
      - glm-4.7  # main agent
      - deepseek-ocr  # OCR transcription agent
```

### Port Allocation
- llama-swap: 8080 (existing)
- vLLM OCR: dynamic via ${PORT} or dedicated 8081

### API Compatibility
- Both provide OpenAI-compatible endpoints
- Multimodal requests require image_url content type
- Special logits processor parameters passed via `vllm_xargs`

## Testing Approach

### Option 1: Python Script Testing (recommended for initial validation)
- Create test project: `/home/philkir/deepseek-ocr/`
- Test script (`test_ocr.py`):
  ```python
  from vllm import LLM, SamplingParams
  from vllm.model_executor.models.deepseek_ocr import NGramPerReqLogitsProcessor
  from PIL import Image

  def main():
      llm = LLM(
          model="unsloth/DeepSeek-OCR",
          enable_prefix_caching=False,
          mm_processor_cache_gb=0,
          logits_processors=[NGramPerReqLogitsProcessor],
          gpu_memory_utilization=0.15,
      )

      image = Image.open("test_image.png").convert("RGB")
      prompt = "<image>\nFree OCR."

      model_input = [
          {
              "prompt": prompt,
              "multi_modal_data": {"image": image}
          }
      ]

      sampling_param = SamplingParams(
          temperature=0.0,
          max_tokens=8192,
          extra_args=dict(
              ngram_size=30,
              window_size=90,
              whitelist_token_ids={128821, 128822},
          ),
          skip_special_tokens=False,
      )

      model_outputs = llm.generate(model_input, sampling_param)
      for output in model_outputs:
          print(output.outputs[0].text)

  if __name__ == "__main__":
      main()
  ```
- Run with: `uv run --python ~/.venv_vllm/bin/python test_ocr.py`
- Model auto-downloads from HuggingFace on first run
- Validates basic OCR functionality before integration

### Option 2: vLLM Serve (for llama-swap integration)
```bash
source ~/.venv_vllm/bin/activate
vllm serve unsloth/DeepSeek-OCR \
  --logits_processors vllm.model_executor.models.deepseek_ocr:NGramPerReqLogitsProcessor \
  --no-enable-prefix-caching \
  --mm-processor-cache-gb 0 \
  --port ${PORT}
```

## Implementation Phases - Detailed Status

### Phase 1: Environment Setup ✅
- [x] Install vLLM 0.13.0 via `uv pip install vllm`
- [x] Create venv at `~/.venv_vllm`
- [x] Verify GPU compatibility
- [x] Test standalone vLLM server (Option 1)
- [x] Move venv to testing directory: `~/deepseek-ocr-testing/.venv_vllm`
- [x] Install DeepSeek-OCR requirements (PyMuPDF, img2pdf, transformers, etc.)

### Phase 1.5: PDF & Complex Document Validation ✅
- [x] Test with fake bank statement (complex financial document)
- [x] Validate text extraction accuracy (100% on financial data)
- [x] Validate table structure preservation (12 transaction rows)
- [x] Confirm layout annotations working (`<|ref|>`, `<|det|>` tags)
- [x] Measure processing time (~2 seconds for complex document)
- [x] Verify memory usage stable (~15GB with gpu_memory_utilization=0.15)
- [x] Confirm no conflicts with concurrent llama.cpp operation

**Testing Summary**:
- Simple image (performance table): ✅ Accurate
- Complex financial document (bank statement): ✅ Excellent
- Table extraction: ✅ Perfect structure
- Numeric data: ✅ 100% accurate
- Layout detection: ✅ Working with bounding boxes

### Phase 2: Service Integration ✅ Complete
- [x] Recreate venv with uv (~/deepseek-ocr-testing/.venv)
- [x] Test vllm serve command manually
- [x] Add DeepSeek-OCR model to llama-swap config.yaml
- [x] Configure ocr-group for concurrent model management
- [x] Validate concurrent model operation (GLM-4.7 + DeepSeek-OCR running)
- [x] Direct vLLM requests work (port 5800 with `unsloth/DeepSeek-OCR`)
- [x] Fix model name mapping in llama-swap using `useModelName` parameter
- [x] Add `--allowed-local-media-path /home/philkir` to vLLM serve command
- [x] Test image OCR workflows via llama-swap proxy (port 8080)
- [x] Verify OpenAI API compatibility

**Memory Usage (Dec 31, 2025)**:
- DeepSeek-OCR (vLLM): 15.46GB VRAM
- GLM-4.7 (llama.cpp): 76.76GB VRAM
- Total: 92.25GB / 97.89GB VRAM (94% utilization)

**Solution Implemented**:
- Added `useModelName: "unsloth/DeepSeek-OCR"` parameter to config.yaml
- llama-swap now correctly maps `deepseek-ocr` alias to vLLM backend model name
- Added `--allowed-local-media-path /home/philkir` to enable local image file access

## Considerations

### Resource Management
- vLLM and llama.cpp may compete for GPU memory
- Consider model unloading policies for OCR model
- Monitor memory usage across both backends
- **Memory allocation**: vLLM caps at ~15GB with `gpu_memory_utilization=0.15`
- **Total usage**: ~80GB (llama.cpp) + ~15GB (vLLM) = ~95GB < 98GB total

### Request Routing
- Multimodal requests need special handling
- OCR-specific prompts (`<image>\nFree OCR.`)
- Ngram processor parameters for optimal performance

### Future Extensibility
- Framework may support other vLLM-only models
- Backend abstraction layer for multiple inference engines
- Unified model lifecycle management

## Troubleshooting

### EngineCore Died Unexpectedly Error

**Issue**: After successful OCR generation, vLLM reports "Engine core proc EngineCore_DP0 died unexpectedly, shutting down client."

**Root Cause**: vLLM engine process starts at import time and isn't properly cleaned up when Python interpreter exits. This is a known issue with vLLM's multiprocessing architecture.

**Solution**: Wrap initialization and generation logic inside a `main()` function and use standard Python entry point pattern:

```python
def main():
    llm = LLM(...)  # Initialize vLLM
    # ... generation logic ...

if __name__ == "__main__":
    main()  # Proper cleanup
```

**References**:
- [vLLM Issue #23517](https://github.com/vllm-project/vllm/issues/23517) - EngineCore died unexpectedly
- RachelOvrani's solution (Nov 13, 2025) - Proper cleanup pattern

### Memory Management Best Practices

1. **Always use proper cleanup pattern**: `if __name__ == "__main__": main()`
2. **Monitor GPU memory**: `nvidia-smi` during and after execution
3. **Set appropriate `gpu_memory_utilization`**: Start with 0.15, adjust based on available VRAM
4. **Test with various image sizes**: Validate stability before production use

## Example vLLM Server Command

```bash
source ~/.venv_vllm/bin/activate
vllm serve unsloth/DeepSeek-OCR \
  --logits_processors vllm.model_executor.models.deepseek_ocr:NGramPerReqLogitsProcessor \
  --no-enable-prefix-caching \
  --mm-processor-cache-gb 0 \
  --port ${PORT}
```

## Example Client Request (OpenAI API)

```python
from openai import OpenAI

client = OpenAI(
    api_key="EMPTY",
    base_url="http://localhost:8000/v1",
    timeout=3600
)

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": "https://example.com/image.png"
                }
            },
            {
                "type": "text",
                "text": "Free OCR."
            }
        ]
    }
]

response = client.chat.completions.create(
    model="unsloth/DeepSeek-OCR",
    messages=messages,
    max_tokens=2048,
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

## References

- [vLLM DeepSeek-OCR Guide](https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-OCR.html)
- [Unsloth DeepSeek-OCR Guide](https://unsloth.ai/docs/models/deepseek-ocr-how-to-run-and-fine-tune#running-deepseek-ocr)
- [Unsloth DeepSeek-OCR Model](https://huggingface.co/unsloth/DeepSeek-OCR)
- [DeepSeek-OCR GitHub Repository](https://github.com/deepseek-ai/DeepSeek-OCR)
- [DeepSeek-OCR Model Card](https://huggingface.co/deepseek-ai/DeepSeek-OCR)

## System Status (Dec 29, 2025 - Dec 31, 2025)

- **llmrig GPU**: RTX PRO 6000 Blackwell (98GB total VRAM)
- **llama-swap**: Running GLM-4.7 + DeepSeek-OCR concurrently
- **vLLM**: 0.13.0 installed in `~/deepseek-ocr-testing/.venv`
- **Test project**: `/home/philkir/deepseek-ocr-testing/`
  - `test_ocr.py` - Validation script with proper cleanup pattern
  - `test_image.png` - Sample image for OCR testing
  - `test_bank_statement.py` - Bank statement OCR test
  - `bank-statement-template-09.jpg` - Fake bank statement for testing
  - `test_llamaswap_ocr.py` - llama-swap integration test script
- **Memory usage**: 92.25GB / 97.89GB VRAM (94% utilization)
- **Phase 1 Status**: ✅ Complete
  - GPU compatibility verified
  - Model downloaded (6.2GB from HuggingFace)
  - OCR functionality validated
  - Proper cleanup pattern implemented
  - No OOM issues with concurrent llama.cpp operation
- **Phase 2 Status**: ✅ Complete (Dec 31, 2025)
   - venv recreated with uv at `~/deepseek-ocr-testing/.venv`
   - vllm serve command tested manually
   - llama-swap config.yaml updated with DeepSeek-OCR model
   - ocr-group configured for concurrent model management
   - Concurrent operation validated (GLM-4.7 + DeepSeek-OCR running)
   - Direct vLLM requests work (port 5800 with `unsloth/DeepSeek-OCR`)
   - **Resolved**: Added `useModelName: "unsloth/DeepSeek-OCR"` parameter
   - **Resolved**: Added `--allowed-local-media-path /home/philkir` for local file access
   - llama-swap proxy requests work (port 8080 with `deepseek-ocr` alias)
- **Phase 3 Status**: 🟡 In Progress
   - Ready for performance benchmarking and extended validation

## Test Results (Dec 29, 2025 - Dec 31, 2025)

### Test 1: Performance Metrics Table (Dec 29, 2025)
- Command: `uv run --python ~/.venv_vllm/bin/python test_ocr.py`
- Image processed: Performance metrics table (7 rows)
- Output: HTML table with text/vision token statistics
- Memory: Properly released after script completion
- No errors: Clean shutdown with `if __name__ == "__main__": main()` pattern

### Test 2: Fake Bank Statement (Dec 30, 2025)
- Command: `cd ~/deepseek-ocr-testing && uv run --python ~/.venv_vllm/bin/python test_bank_statement.py`
- Image: Bank statement template with complex financial layout
- Output: Complete markdown with layout annotations (`<|ref|>`, `<|det|>`)
- Extracted accurately:
  - Personal information (name, address)
  - Account summary (opening/closing balances)
  - Complete transaction table (12 rows: dates, descriptions, withdrawals, deposits, balances)
  - Contact information and branch details
- Processing time: ~2 seconds
- Memory usage: ~15GB (gpu_memory_utilization=0.15)
- Note: Model transcribed text mentioning QR codes but did not detect/extract QR code images

### Test 3: llama-swap Integration (Dec 31, 2025)
- **Direct vLLM requests (port 5800)**: ✅ Working
  - Model name: `unsloth/DeepSeek-OCR`
  - OCR functionality confirmed with base64 encoded images
  - Proper table extraction from test image
- **llama-swap proxy requests (port 8080)**: ✅ Working (Jan 1, 2026)
  - Model name in config: `deepseek-ocr` (alias)
  - Solution: Added `useModelName: "unsloth/DeepSeek-OCR"` parameter
  - Added `--allowed-local-media-path /home/philkir` for local file access
  - Response time: 34.79s for performance table image
  - OCR output: Accurate HTML table extraction

### Key Findings
1. vLLM properly respects `gpu_memory_utilization=0.15` (~15GB cap)
2. No OOM conflicts with llama.cpp running concurrently
3. Cleanup pattern eliminates "EngineCore died unexpectedly" error
4. OCR accuracy: Successfully extracted complex tabular data with 100% text accuracy
5. Layout preservation: Preserves document structure with bounding box annotations
6. Financial data: All monetary amounts correctly transcribed (e.g., "5,234.09", "2100.00")
7. Table structure: HTML table format maintains proper column alignment
8. **Resolved**: llama-swap `useModelName` parameter enables vLLM backend mapping
9. vLLM backend requires full HuggingFace model name (`unsloth/DeepSeek-OCR`)
10. `--allowed-local-media-path` required for local image file access via llama-swap

---

**Document Version**: 2.0
**Last Updated**: 2025-12-31
**Status**: Implementation Phase - DeepSeek-OCR Integration Complete, Subagent Development In Progress
