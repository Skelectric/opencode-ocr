# Simplified OCR Routing Plan - Model-Based Configuration

## Problem Statement

The current implementation uses VRAM-aware logic to determine whether to route OCR requests to DeepSeek-OCR or the currently-loaded model. This requires shell access to execute `nvidia-smi` on the llmrig server, which is a security risk for an agentic PDF-OCR tool of this scope.

We need to simplify the implementation to use a model-based configuration approach.

## Key Insights

1. **DeepSeek-OCR is a parallel model**, not a fallback - it's loaded alongside the main model
2. **VRAM availability varies by model**: Some models (like Qwen3.5 with all expert layers on GPU) consume all VRAM, leaving none for DeepSeek-OCR
3. **User switches models frequently**: A global flag requires constant manual updates
4. **Per-model configuration needed**: Different models have different VRAM requirements and capabilities
5. **Default to current model**: Safer default that doesn't assume DeepSeek-OCR availability

## Proposed Solution

### Model-Based Routing Configuration

Create a JSON configuration file that maps model IDs to their preferred OCR method:

```json
{
  "ocr_routing": {
    "kimi-k2.5": "deepseek-ocr",
    "kimi-k2.5-abliterated": "deepseek-ocr",
    "default": "current_model"
  }
}
```

### Routing Logic

```
PDF Input → pdf_ocr_backend.py
                    ↓
         Query /running for current model
                    ↓
         Look up model in routing config
                    ↓
            ┌───────┴───────┐
            ↓               ↓
    "deepseek-ocr"    "current_model"
            ↓               ↓
    Use DeepSeek-OCR    Check /props for vision=true
            ↓               ↓
       ┌────┴────┐      ┌───┴───┐
       ↓         ↓      ↓       ↓
    Success    Fail   Yes      No
       ↓         ↓      ↓       ↓
   Return    Exit 1  Use      Exit 3
   Result    (Error) Current  (No OCR
                     Model    Support)
```

### Behavior Matrix

| Config Value | DeepSeek-OCR Success | Current Model Vision | Result |
|--------------|----------------------|----------------------|--------|
| "deepseek-ocr" | Yes | N/A | Use DeepSeek-OCR (Exit 0) |
| "deepseek-ocr" | No | N/A | Exit 1 (DeepSeek-OCR error) |
| "current_model" | N/A | Yes | Use Current Model (Exit 0) |
| "current_model" | N/A | No | Exit 3 (No OCR support) |
| Not in config | N/A | Yes | Use Current Model (Exit 0) |
| Not in config | N/A | No | Exit 3 (No OCR support) |

## Implementation Changes

### 1. Remove VRAM Detection

**Delete:**
- `check_vram_availability()` function
- `PDF_OCR_VRAM_THRESHOLD_GB` environment variable
- All nvidia-smi subprocess calls
- VRAM-related validation in `validate_environment_variables()`

### 2. Create Routing Configuration File

**New file: `pdf-ocr/tool/ocr_routing.json`**

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

### 3. Add Configuration Loader

```python
def load_ocr_routing_config(config_path: Optional[str] = None) -> dict:
    """
    Load OCR routing configuration from JSON file.
    
    Args:
        config_path: Path to the routing config file. If None, uses default location.
    
    Returns:
        dict: Routing configuration with model mappings
    """
    if config_path is None:
        tool_dir = Path(__file__).parent
        config_path = tool_dir / "ocr_routing.json"
    
    default_config = {"ocr_routing": {}, "default": "current_model"}
    
    if not Path(config_path).exists():
        logger.warning(f"Routing config not found at {config_path}, using defaults")
        return default_config
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Validate config structure
        if "ocr_routing" not in config:
            config["ocr_routing"] = {}
        if "default" not in config:
            config["default"] = "current_model"
        
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in routing config: {e}")
        return default_config
    except Exception as e:
        logger.error(f"Error loading routing config: {e}")
        return default_config


def get_ocr_method_for_model(model_id: str, config: dict) -> str:
    """
    Determine OCR method for a given model based on routing configuration.
    
    Args:
        model_id: The current model ID
        config: The routing configuration dictionary
    
    Returns:
        str: "deepseek-ocr" or "current_model"
    """
    routing = config.get("ocr_routing", {})
    default = config.get("default", "current_model")
    
    # Check for exact match
    if model_id in routing:
        return routing[model_id]
    
    # Check for partial match (e.g., "kimi-k2.5" matches "ik_llama.cpp/kimi-k2.5-experimental")
    for pattern, method in routing.items():
        if pattern in model_id or model_id in pattern:
            return method
    
    # Return default
    return default
```

### 4. Update Validation

Update `validate_environment_variables()` to:
- Remove VRAM threshold validation
- Add validation for routing config file existence (warning only)

### 5. Rewrite Routing Function

```python
def route_ocr_request(pdf_path: str, output_format: str) -> str:
    """
    Route OCR request based on model-based configuration.
    
    Args:
        pdf_path: Path to the PDF file
        output_format: Output format (markdown or text)
    
    Returns:
        str: OCR result text
    
    Exits:
        0: Success (DeepSeek-OCR or current multimodal model used)
        1: General error (file not found, processing error, DeepSeek-OCR failure, etc.)
        3: NO_OCR_SUPPORT (current_model routing but model lacks vision support)
    """
    base_url = os.getenv("DEEPSEEK_OCR_BASE_URL")
    if not base_url:
        raise Exception("DEEPSEEK_OCR_BASE_URL not set")
    
    # Load routing configuration
    routing_config = load_ocr_routing_config()
    
    # Get current model
    current_model = get_current_model(base_url)
    if not current_model:
        raise Exception("No model currently loaded")
    
    # Determine OCR method based on configuration
    ocr_method = get_ocr_method_for_model(current_model, routing_config)
    
    logger.info(f"Model: {current_model}, OCR method: {ocr_method}")
    
    if ocr_method == "deepseek-ocr":
        # Use DeepSeek-OCR
        logger.info(f"Routing to DeepSeek-OCR based on config for {current_model}")
        try:
            return process_with_deepseek_ocr(pdf_path, output_format)
        except Exception as e:
            # DeepSeek-OCR failed - this is a general error (Exit 1)
            logger.error(f"DeepSeek-OCR failed: {e}")
            raise
    else:
        # Use current model - check if it supports vision
        logger.info(f"Routing to current model based on config for {current_model}")
        
        if check_multimodal_support(base_url, current_model):
            return process_with_current_model(
                pdf_path, output_format, current_model, base_url
            )
        else:
            # Current model doesn't support vision - Exit 3
            error_msg = (
                f"NO_OCR_SUPPORT: Model '{current_model}' is configured to use "
                f"current_model for OCR but does not support multimodal/vision capabilities. "
                f"Add '{current_model}' to ocr_routing.json with 'deepseek-ocr' value "
                f"to use DeepSeek-OCR instead."
            )
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            sys.exit(3)
```

### 6. Update deploy-tool.sh

Replace VRAM threshold prompt with routing config setup:

```bash
# Remove VRAM threshold section entirely

# Add routing config creation
ROUTING_CONFIG="$TOOL_DIR/pdf-ocr/tool/ocr_routing.json"
if [ ! -f "$ROUTING_CONFIG" ]; then
    echo ""
    echo "Creating OCR routing configuration..."
    echo "This file maps models to their preferred OCR method."
    
    cat > "$ROUTING_CONFIG" << 'EOF'
{
  "_comment": "OCR Routing Configuration - Maps model IDs to preferred OCR method",
  "_routing_options": {
    "deepseek-ocr": "Use DeepSeek-OCR model (requires sufficient VRAM)",
    "current_model": "Use the currently loaded model (requires vision support)"
  },
  "ocr_routing": {},
  "default": "current_model"
}
EOF
    
    echo "Created default routing config at $ROUTING_CONFIG"
    echo "Edit this file to enable DeepSeek-OCR for specific models."
fi
```

### 7. Update Error Messages

**Scenario A: DeepSeek-OCR configured but fails**
```
Error processing PDF: <exception message>
Exit code: 1
```

**Scenario B: Current model configured but has no vision support**
```
NO_OCR_SUPPORT: Model 'model-name' is configured to use current_model for OCR but does not support multimodal/vision capabilities. Add 'model-name' to ocr_routing.json with 'deepseek-ocr' value to use DeepSeek-OCR instead.
Exit code: 3
```

## Exit Codes

| Exit Code | Meaning | Scenario |
|-----------|---------|----------|
| **0** | Success | DeepSeek-OCR used OR current multimodal model used |
| **1** | General Error | File not found, API unreachable, processing error, DeepSeek-OCR failure, etc. |
| **3** | **NO_OCR_SUPPORT** | Current model configured to use current_model routing but lacks vision support |

## Configuration Examples

### Example A: Enable DeepSeek-OCR for Kimi models
```json
{
  "ocr_routing": {
    "ik_llama.cpp/kimi-k2.5": "deepseek-ocr",
    "ik_llama.cpp/kimi-k2.5-experimental": "deepseek-ocr"
  },
  "default": "current_model"
}
```

### Example B: Disable DeepSeek-OCR entirely (always use current model)
```json
{
  "ocr_routing": {},
  "default": "current_model"
}
```

### Example C: Enable DeepSeek-OCR for all models by default
```json
{
  "ocr_routing": {},
  "default": "deepseek-ocr"
}
```

### Example D: Mixed setup with specific overrides
```json
{
  "ocr_routing": {
    "ik_llama.cpp/kimi-k2.5": "deepseek-ocr",
    "ik_llama.cpp/qwen3.5": "current_model",
    "ik_llama.cpp/llama-vision": "current_model"
  },
  "default": "deepseek-ocr"
}
```

## Files to Modify

1. **pdf_ocr_backend.py**
   - Remove `check_vram_availability()` function
   - Update `validate_environment_variables()`
   - Add `load_ocr_routing_config()` function
   - Add `get_ocr_method_for_model()` function
   - Rewrite `route_ocr_request()` with model-based logic
   - Remove VRAM-related imports (subprocess)
   - Add json import

2. **.env.example**
   - Remove `PDF_OCR_VRAM_THRESHOLD_GB`
   - No new env vars needed (config is in JSON file)

3. **deploy-tool.sh**
   - Remove VRAM threshold prompt
   - Add routing config creation prompt
   - Create default `ocr_routing.json`

4. **tests/test_backend.py**
   - Remove VRAM-related tests
   - Add tests for routing config loading
   - Add tests for model-based routing logic
   - Update exit code 3 tests

## Migration Path

### From Current Implementation

1. Remove `PDF_OCR_VRAM_THRESHOLD_GB` from `.env` (optional - will be ignored)
2. Create `ocr_routing.json` with desired model mappings
3. Test with your current model setup
4. Add models to config as needed

### Backward Compatibility

- `PDF_OCR_VRAM_THRESHOLD_GB` will be ignored (no error)
- Default behavior: `current_model` (safe default)
- No routing config = all models use current_model

## Success Criteria

1. ✅ No shell access required (no nvidia-smi calls)
2. ✅ Model-based configuration for routing
3. ✅ Clear error messages when OCR is not possible
4. ✅ Exit code 3 for "no OCR support" scenarios
5. ✅ Endpoint queries preserved for model capability checks
6. ✅ DeepSeek-OCR treated as parallel model, not fallback
7. ✅ Default behavior is safe (use current model)
8. ✅ Per-model configuration allows frequent model switching

## Security Benefits

- No shell command execution required
- No system information gathering (VRAM queries)
- All routing decisions based on user configuration and API responses
- Reduced attack surface for agentic tool

---

*Plan created: 2026-03-03*
*Target implementation: pdf_ocr_backend.py v2.1*
</content>