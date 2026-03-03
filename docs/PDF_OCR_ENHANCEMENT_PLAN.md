# PDF OCR Tool Enhancement Plan

## Problem Statement

The current PDF OCR tool implementation has the following limitations:

1. **Hardcoded Model Dependency**: Always attempts to load `deepseek-ocr` model regardless of VRAM availability
2. **No Fallback Mechanism**: Fails entirely when DeepSeek-OCR cannot be loaded due to insufficient VRAM
3. **Static Configuration**: Uses only `DEEPSEEK_OCR_BASE_URL` environment variable with no dynamic model selection
4. **Context Ignorance**: Doesn't check if currently loaded model supports multimodal/vision capabilities

## Current Architecture Issues

### VRAM Constraints
- **Kimi-K2.5**: Configured with expert layers offloaded to RAM, leaving sufficient VRAM for DeepSeek-OCR
- **Qwen3.5**: Configured with all expert layers on GPU (for maximum speed), leaving insufficient VRAM for parallel DeepSeek-OCR loading

### Current Flow
```
PDF Input → pdf-ocr.ts → pdf_ocr_backend.py → DeepSeek-OCR API
                                     ↓
                               Hardcoded Model Call
```

## Proposed Solution Architecture

### Dynamic Model Selection Strategy

Implement a routing system that:

1. **Evaluates VRAM Availability**: Check if there's enough VRAM (17 GB) to load DeepSeek-OCR
2. **Routes Requests Intelligently**:
   - **Primary Route**: Use DeepSeek-OCR (if VRAM available)
   - **Secondary Route**: Use currently loaded multimodal model (if it supports vision)
   - **Error Route**: Exit with code 3 if neither option is viable

### New Flow
```
PDF Input → pdf-ocr.ts → pdf_ocr_backend.py
                                     ↓
                              Check Free VRAM
                                     ↓
                           ┌─────────┴─────────┐
                           ↓                   ↓
                    VRAM >= 17 GB         VRAM < 17 GB
                           ↓                   ↓
                    Use DeepSeek-OCR    Query Current Model
                           ↓                   ↓
                    Process PDF         Check /upstream/{model}/props
                                             ↓
                                      ┌──────┴──────┐
                                      ↓             ↓
                                vision=true    vision=false
                                      ↓             ↓
                               Use Current      Exit Code 3
                               Model            (No Multimodal)
                                      ↓
                               Process PDF
```

## Implementation Plan

### Phase 1: Enhanced Backend (pdf_ocr_backend.py)

#### 1.1 VRAM Detection
```python
def check_vram_availability() -> Tuple[bool, int]:
    """Check if sufficient VRAM is available for DeepSeek-OCR (17 GB threshold)"""
    # Query nvidia-smi for free VRAM
    # Return (has_enough_vram, free_mb)
    pass
```

#### 1.2 Current Model Detection
```python
def get_current_model(base_url: str) -> Optional[str]:
    """Query ik_llama.cpp /running endpoint for currently loaded model"""
    pass

def check_multimodal_support(base_url: str, model_id: str) -> bool:
    """Query /upstream/{model_id}/props for modalities.vision"""
    # Returns True if model supports vision/multimodal
    pass
```

#### 1.3 Model Router
```python
def route_ocr_request(pdf_path: str, output_format: str) -> str:
    """
    Route OCR request based on VRAM and model capabilities.
    
    Returns:
        str: OCR result text
    
    Exits:
        0: Success (DeepSeek-OCR or current multimodal model used)
        1: General error (file not found, processing error, etc.)
        3: INSUFFICIENT_VRAM_NO_MULTIMODAL (not enough VRAM and current model lacks vision support)
    """
    # Get configurable threshold (default: 17 GB)
    vram_threshold_gb = int(os.getenv("PDF_OCR_VRAM_THRESHOLD_GB", "17"))
    vram_threshold_mb = vram_threshold_gb * 1024
    
    free_vram_mb = check_vram_availability()
    
    if free_vram_mb >= vram_threshold_mb:
        # Use DeepSeek-OCR
        return process_with_deepseek_ocr(pdf_path, output_format)
    else:
        # Check if current model supports multimodal
        current_model = get_current_model(IK_LLAMA_BASE_URL)
        if current_model and check_multimodal_support(IK_LLAMA_BASE_URL, current_model):
            # Use current multimodal model
            return process_with_current_model(pdf_path, output_format, current_model)
        else:
            # Exit with code 3
            error_msg = f"INSUFFICIENT_VRAM_NO_MULTIMODAL: DeepSeek-OCR requires ~{vram_threshold_gb}GB VRAM but only {free_vram_mb//1024} GB available. Current model '{current_model}' does not support multimodal/vision capabilities."
            print(error_msg, file=sys.stderr)
            sys.exit(3)
```

#### 1.4 Model-Specific Prompt Adaptation
```python
PROMPT_TEMPLATES = {
    'deepseek-ocr': {
        'system': None,
        'user': 'Free OCR.',
        'extra_body': {
            'skip_special_tokens': False,
            'vllm_xargs': {
                'ngram_size': 30,
                'window_size': 90,
                'whitelist_token_ids': [128821, 128822],
            },
        },
    },
    'default_multimodal': {
        'system': 'You are an OCR assistant. Extract all text from the image accurately.',
        'user': 'Please perform OCR on this image and extract all visible text. Format the output as markdown.',
        'extra_body': None,
    },
}
```

### Phase 2: Configuration Enhancement

#### 2.1 Environment Variables
```bash
# DeepSeek-OCR Configuration (existing)
DEEPSEEK_OCR_BASE_URL=http://localhost:8080/v1

# ik_llama.cpp Integration (new)
IK_LLAMA_BASE_URL=http://192.168.104.222:8080  # For querying loaded models

# VRAM Threshold (new - configurable, defaults to 17 GB)
PDF_OCR_VRAM_THRESHOLD_GB=17  # Minimum free VRAM required for DeepSeek-OCR
```

#### 2.2 deploy-tool.sh Updates
Update the deployment script to prompt for the new environment variable:

```bash
# In deploy-tool.sh, add to the .env creation section:
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "No .env file found. Please provide configuration."
    
    # Existing DeepSeek-OCR endpoint prompt
    read -p "Enter DeepSeek-OCR endpoint URL (e.g., http://localhost:8080/v1): " ENDPOINT
    if [ -z "$ENDPOINT" ]; then
        echo "Warning: No endpoint provided. Creating .env with placeholder."
        ENDPOINT="http://your-endpoint:8080/v1"
    fi
    echo "DEEPSEEK_OCR_BASE_URL=\"$ENDPOINT\"" > "$ENV_FILE"
    
    # New ik_llama.cpp endpoint prompt
    echo ""
    read -p "Enter ik_llama.cpp endpoint URL (e.g., http://192.168.104.222:8080): " IK_LLAMA_ENDPOINT
    if [ -z "$IK_LLAMA_ENDPOINT" ]; then
        echo "Warning: No ik_llama endpoint provided. Using placeholder."
        IK_LLAMA_ENDPOINT="http://localhost:8080"
    fi
    echo "IK_LLAMA_BASE_URL=\"$IK_LLAMA_ENDPOINT\"" >> "$ENV_FILE"
    
    # New VRAM threshold prompt
    echo ""
    read -p "Enter VRAM threshold in GB for DeepSeek-OCR [default: 17]: " VRAM_THRESHOLD
    if [ -z "$VRAM_THRESHOLD" ]; then
        VRAM_THRESHOLD="17"
    fi
    echo "PDF_OCR_VRAM_THRESHOLD_GB=\"$VRAM_THRESHOLD\"" >> "$ENV_FILE"
    
    echo ".env file created at $ENV_FILE"
fi
```

#### 2.2 API Endpoints Used
- **Check loaded model**: `GET http://192.168.104.222:8080/running`
- **Check multimodal support**: `GET http://192.168.104.222:8080/upstream/{model-id}/props`
  - Response includes: `{"modalities": {"vision": true/false, "audio": true/false}}`
- **OCR processing**: `POST http://192.168.104.222:8080/upstream/{model-id}/v1/chat/completions`

### Phase 3: Frontend (No Changes Required)

The TypeScript frontend (`pdf-ocr.ts`) requires **no changes**. It will:
- Pass through error messages from the Python backend as-is
- Exit code 3 errors will be returned to the AI conversation naturally
- No special error handling or structured error parsing needed

### Phase 4: VRAM Detection Implementation

#### 4.1 ik_llama.cpp Integration
Query the `/running` endpoint to get:
- Currently loaded models
- GPU memory usage
- Model capabilities (multimodal support)

#### 4.2 nvidia-smi Fallback
If ik_llama.cpp doesn't provide VRAM info:
```python
def get_vram_info_nvidia():
    """Get VRAM info using nvidia-smi"""
    import subprocess
    result = subprocess.run(
        ['nvidia-smi', '--query-gpu=memory.free,memory.total', '--format=csv,noheader,nounits'],
        capture_output=True, text=True
    )
    # Parse output
```

### Phase 5: Testing Strategy

#### 5.1 Unit Tests
- VRAM calculation from nvidia-smi output
- Current model detection from /running endpoint
- Multimodal support check from /props endpoint
- Prompt template selection

#### 5.2 Integration Tests
- End-to-end PDF processing with DeepSeek-OCR (sufficient VRAM)
- End-to-end PDF processing with current multimodal model (insufficient VRAM)
- Error handling when current model lacks multimodal support

#### 5.3 Test Scenarios
1. **DeepSeek-OCR Available**: Sufficient VRAM (>= 17 GB), uses DeepSeek-OCR → Exit 0
2. **Current Multimodal Model**: Insufficient VRAM (< 17 GB), current model has vision=true → Exit 0
3. **No Multimodal Fallback**: Insufficient VRAM (< 17 GB), current model has vision=false → Exit 3
4. **General Error**: File not found, API unreachable, processing error → Exit 1

## Configuration Example

### Required .env Configuration
```bash
# DeepSeek-OCR endpoint (existing)
DEEPSEEK_OCR_BASE_URL=http://localhost:8080/v1

# ik_llama.cpp endpoint for model detection (new)
IK_LLAMA_BASE_URL=http://192.168.104.222:8080
```

## Exit Codes

| Exit Code | Meaning | Scenario |
|-----------|---------|----------|
| **0** | Success | DeepSeek-OCR used OR current multimodal model used |
| **1** | General Error | File not found, API unreachable, processing error, etc. |
| **3** | INSUFFICIENT_VRAM_NO_MULTIMODAL | VRAM < 17 GB AND current model lacks vision support |

## Migration Path

### Backward Compatibility
- All existing environment variables continue to work (DEEPSEEK_OCR_BASE_URL)
- New environment variable required: IK_LLAMA_BASE_URL
- If IK_LLAMA_BASE_URL is not set, behavior falls back to original (always attempt DeepSeek-OCR)

## Success Criteria

1. ✅ DeepSeek-OCR used when VRAM >= 17 GB available
2. ✅ Current multimodal model used when VRAM < 17 GB AND model supports vision
3. ✅ Exit code 3 returned when VRAM < 17 GB AND current model lacks multimodal support
4. ✅ Error message clearly explains the situation
5. ✅ Frontend passes through error without modification

## Future Enhancements

1. **Quality Metrics**: Compare OCR accuracy between models
2. **Performance Monitoring**: Track processing times per model
3. **Multi-GPU Support**: Distribute models across multiple GPUs
4. **Model Preloading**: Preload DeepSeek-OCR when VRAM becomes available
5. **User Preference Learning**: Remember successful model choices per document type

---

## Implementation Notes

### Key Technical Decisions

1. **Single Backend File**: Keep all logic in `pdf_ocr_backend.py` to minimize changes
2. **Environment-Based Config**: Use env vars for easy Docker/container compatibility
3. **Graceful Degradation**: Always attempt to process PDF, even if not optimally
4. **Logging**: Add verbose logging for debugging model selection decisions

### Files to Modify
- `pdf_ocr_backend.py` - Main implementation (add VRAM checking, model detection, routing logic)
- `.env.example` - Document new IK_LLAMA_BASE_URL variable

### Dependencies
- No new Python dependencies required
- Uses existing `openai` client for all model communication
- Leverages ik_llama.cpp's OpenAI-compatible API

---

*Plan created: 2026-03-03*
*Target implementation: pdf_ocr_backend.py v2.0*
