# OCR Routing Implementation Checklist

## Setup and Configuration

- [x] Verify existing file locations:
  - [x] pdf_ocr_backend.py
  - [x] deploy-tool.sh
  - [x] tests/test_backend.py
  - [x] pdf-ocr/tool/.env.example

## Phase 1: Remove VRAM Detection

- [x] Open pdf_ocr_backend.py
- [x] Locate and delete check_vram_availability() function
- [x] Remove all nvidia-smi subprocess calls from the codebase
- [x] Remove PDF_OCR_VRAM_THRESHOLD_GB environment variable references
- [x] Update validate_environment_variables() to remove VRAM threshold validation
- [x] Remove subprocess import if no longer needed for other purposes
- [x] Remove PDF_OCR_VRAM_THRESHOLD_GB line from pdf-ocr/tool/.env.example

### Testing Phase 1

- [x] Verify code compiles without syntax errors
- [x] Run existing tests to ensure VRAM-related functionality is removed
- [x] Verify .env.example is valid and complete without VRAM variable
- [x] Verify no other environment variables need updating in .env.example

## Phase 2: Create Routing Configuration File

- [x] Create new file pdf-ocr/tool/ocr_routing.json
- [x] Add _comment field explaining the purpose
- [x] Add _routing_options field documenting routing options:
  - [x] deepseek-ocr: Use DeepSeek-OCR model (requires sufficient VRAM)
  - [x] current_model: Use the currently loaded model (requires vision support)
- [x] Add ocr_routing object with model mappings:
  - [x] ik_llama.cpp/kimi-k2.5: deepseek-ocr
  - [x] ik_llama.cpp/kimi-k2.5-experimental: deepseek-ocr
- [x] Add default: current_model

### Testing Phase 2

- [x] Validate JSON syntax
- [x] Verify file is readable by Python json module
- [x] Validate config schema:
  - [x] Verify all values in ocr_routing are either "deepseek-ocr" or "current_model"
  - [x] Verify default value is either "deepseek-ocr" or "current_model"
  - [x] Verify no invalid keys in ocr_routing object

## Phase 3: Add Configuration Loader

- [x] Import json module in pdf_ocr_backend.py
- [x] Import Path from pathlib if not already imported
- [x] Implement load_ocr_routing_config(config_path: Optional[str] = None) -> dict:
  - [x] If config_path is None, use default location: Path(__file__).parent / ocr_routing.json
  - [x] Define default_config = {ocr_routing: {}, default: current_model}
  - [x] If config file does not exist:
    - [x] Log warning: Routing config not found at {config_path}, using defaults
    - [x] Return default_config
  - [x] Try to load JSON:
    - [x] If json.JSONDecodeError:
      - [x] Log error: Invalid JSON in routing config: {e}
      - [x] Return default_config
    - [x] If other Exception:
      - [x] Log error: Error loading routing config: {e}
      - [x] Return default_config
  - [x] Validate config structure:
    - [x] If ocr_routing not in config, set to {}
    - [x] If default not in config, set to current_model
  - [x] Return validated config

- [x] Implement get_ocr_method_for_model(model_id: str, config: dict) -> str:
  - [x] Get routing dict: config.get(ocr_routing, {})
  - [x] Get default: config.get(default, current_model)
  - [x] Check for exact match:
    - [x] If model_id in routing, return routing[model_id]
  - [x] Check for partial match:
    - [x] Loop through routing.items()
    - [x] If pattern in model_id or model_id in pattern, return method
  - [x] Return default

### Testing Phase 3

- [x] Unit test: load_ocr_routing_config() with existing valid config file
- [x] Unit test: load_ocr_routing_config() with non-existent config file
- [x] Unit test: load_ocr_routing_config() with invalid JSON
- [x] Unit test: load_ocr_routing_config() with missing ocr_routing key
- [x] Unit test: load_ocr_routing_config() with missing default key
- [x] Unit test: get_ocr_method_for_model() with exact model match
- [x] Unit test: get_ocr_method_for_model() with partial model match
- [x] Unit test: get_ocr_method_for_model() with no match (should return default)
- [x] Unit test: get_ocr_method_for_model() with empty config

## Phase 4: Update Validation

- [x] Update validate_environment_variables() function:
  - [x] Remove VRAM threshold validation logic
  - [x] Add validation for routing config file existence
    - [x] If config file does not exist, log warning (not error)

### Testing Phase 4

- [x] Test: Verify no errors when VRAM env var is set (should be ignored)
- [x] Test: Verify warning logged when routing config missing
- [x] Test: Verify no warning when routing config present

## Phase 5: Rewrite Routing Function

- [x] Rewrite route_ocr_request(pdf_path: str, output_format: str) -> str:
  - [x] Get base_url = os.getenv(DEEPSEEK_OCR_BASE_URL)
  - [x] If base_url not set, raise Exception(DEEPSEEK_OCR_BASE_URL not set)
  - [x] Load routing configuration: routing_config = load_ocr_routing_config()
  - [x] Get current model: current_model = get_current_model(base_url)
  - [x] If no current model, raise Exception(No model currently loaded)
  - [x] Determine OCR method: ocr_method = get_ocr_method_for_model(current_model, routing_config)
  - [x] Log: Model: {current_model}, OCR method: {ocr_method}
  
  - [x] If ocr_method == deepseek-ocr:
    - [x] Log: Routing to DeepSeek-OCR based on config for {current_model}
    - [x] Try:
      - [x] Return process_with_deepseek_ocr(pdf_path, output_format)
    - [x] Except Exception:
      - [x] Log error: DeepSeek-OCR failed: {e}
      - [x] Re-raise exception (Exit 1)
  
  - [x] Else (use current model):
    - [x] Log: Routing to current model based on config for {current_model}
    - [x] If check_multimodal_support(base_url, current_model):
      - [x] Return process_with_current_model(pdf_path, output_format, current_model, base_url)
    - [x] Else:
      - [x] Construct error message:
        NO_OCR_SUPPORT: Model {current_model} is configured to use current_model for OCR but does not support multimodal/vision capabilities. Add {current_model} to ocr_routing.json with deepseek-ocr value to use DeepSeek-OCR instead.
      - [x] Log error with message
      - [x] Print message to stderr
      - [x] sys.exit(3)

### Testing Phase 5

- [x] Test: route_ocr_request() with DEEPSEEK_OCR_BASE_URL not set (should raise exception)
- [x] Test: route_ocr_request() with no model loaded (should raise exception)
- [x] Test: route_ocr_request() with deepseek-ocr configured and successful
- [x] Test: route_ocr_request() with deepseek-ocr configured and failing (should raise exception, Exit 1)
- [x] Test: route_ocr_request() with current_model configured and vision support (should succeed, Exit 0)
- [x] Test: route_ocr_request() with current_model configured but no vision support (should exit 3)
- [x] Test: route_ocr_request() with model not in config and vision support (should succeed, Exit 0)
- [x] Test: route_ocr_request() with model not in config and no vision support (should exit 3)
- [x] Test: Verify error message format for DeepSeek-OCR failure matches specification
- [x] Test: Verify error message format for NO_OCR_SUPPORT (Exit 3) matches specification exactly
- [x] Test: Verify exit codes match specification (0, 1, 3)

## Phase 6: Update deploy-tool.sh

- [x] Open deploy-tool.sh
- [x] Locate and remove entire VRAM threshold prompt section
- [x] Add routing config creation section:
  - [x] Define ROUTING_CONFIG=$TOOL_DIR/pdf-ocr/tool/ocr_routing.json
  - [x] If file does not exist ([ ! -f "$ROUTING_CONFIG" ]):
    - [x] Print empty line
    - [x] Print: Creating OCR routing configuration...
    - [x] Print: This file maps models to their preferred OCR method.
    - [x] Create default config file with heredoc containing JSON with _comment, _routing_options, ocr_routing (empty), and default
    - [x] Print: Created default routing config at $ROUTING_CONFIG
    - [x] Print: Edit this file to enable DeepSeek-OCR for specific models.
- [x] **FIXED**: Add copy of ocr_routing.json from repo to tool directory during deployment

### Testing Phase 6

- [x] Test: Run deploy-tool.sh when config does not exist (should create default)
- [x] Test: Run deploy-tool.sh when config exists (should skip creation)
- [x] Test: Verify created config is valid JSON
- [x] Test: Verify no VRAM threshold prompts appear
- [x] Test: Verify ocr_routing.json is copied to $TOOL_DIR/pdf-ocr/tool/

## Phase 7: Update Documentation

- [x] Update README.md:
  - [x] Remove references to VRAM threshold configuration
  - [x] Add section on model-based OCR routing
  - [x] Document ocr_routing.json configuration format
  - [x] Add examples for common use cases
  - [x] Update troubleshooting section with new error messages

### Testing Phase 7

- [x] Verify README.md examples work as documented
- [x] Verify all links in documentation are valid
- [x] Verify code snippets in documentation match actual implementation

## Phase 8: Update Tests (test_backend.py)

- [x] Open tests/test_backend.py
- [x] Remove all VRAM-related tests
- [x] Remove tests for check_vram_availability()
- [x] Remove tests for PDF_OCR_VRAM_THRESHOLD_GB

### Add New Tests

- [x] Add tests for load_ocr_routing_config():
  - [x] Test loading valid config file
  - [x] Test loading non-existent config file (returns defaults)
  - [x] Test loading invalid JSON (returns defaults)
  - [x] Test config with missing keys (adds defaults)

- [x] Add tests for get_ocr_method_for_model():
  - [x] Test exact model match
  - [x] Test partial model match (pattern in model_id)
  - [x] Test partial model match (model_id in pattern)
  - [x] Test no match returns default
  - [x] Test empty routing dict returns default

- [x] Add tests for route_ocr_request() model-based routing:
  - [x] Test with deepseek-ocr configuration and success
  - [x] Test with deepseek-ocr configuration and failure
  - [x] Test with current_model configuration and vision support
  - [x] Test with current_model configuration and no vision support (Exit 3)
  - [x] Test with model not in config and vision support
  - [x] Test with model not in config and no vision support (Exit 3)

- [x] Update exit code 3 tests:
  - [x] Verify Exit 3 only occurs when current_model configured but no vision support
  - [x] Verify error message includes model name and configuration instructions

### Testing Phase 8

- [x] Run all new tests and verify they pass
- [x] Run full test suite to ensure no regressions

## Phase 9: Integration Testing

- [ ] Test complete workflow with Kimi model configured for deepseek-ocr:
  - [ ] Verify routing to DeepSeek-OCR
  - [ ] Verify successful PDF processing
  - [ ] Verify Exit 0 on success
  - [ ] Verify Exit 1 on DeepSeek-OCR failure

- [ ] Test complete workflow with model configured for current_model:
  - [ ] Verify routing to current model
  - [ ] Verify vision capability check via /props endpoint
  - [ ] Verify Exit 0 when vision supported
  - [ ] Verify Exit 3 when vision not supported
  - [ ] Verify correct error message on Exit 3

- [ ] Test with model not in config:
  - [ ] Verify default behavior (current_model)
  - [ ] Verify correct exit codes

- [ ] Test migration path:
  - [ ] Verify PDF_OCR_VRAM_THRESHOLD_GB is ignored (no errors)
  - [ ] Verify default behavior without config file
  - [ ] Test adding models to config after initial setup

## Phase 10: Final Verification

- [x] Verify all VRAM-related code removed:
  - [x] No check_vram_availability() function
  - [x] No nvidia-smi subprocess calls
  - [x] No PDF_OCR_VRAM_THRESHOLD_GB references
  - [x] No VRAM validation in validate_environment_variables()

- [x] Verify routing logic matches specification:
  - [x] Model lookup in config
  - [x] Exact and partial matching
  - [x] Default fallback behavior
  - [x] DeepSeek-OCR path
  - [x] Current model path with vision check

- [x] Verify exit codes:
  - [x] Exit 0: Success (DeepSeek-OCR or current multimodal model)
  - [x] Exit 1: General error (file not found, API error, DeepSeek-OCR failure)
  - [x] Exit 3: NO_OCR_SUPPORT (current_model routing but no vision)

- [x] Verify error messages match specification exactly

- [x] Verify backward compatibility:
  - [x] Old .env files with VRAM threshold work (variable ignored)
  - [x] No config file defaults to current_model

## Migration Checklist (User-facing)

- [ ] Remove PDF_OCR_VRAM_THRESHOLD_GB from .env (optional)
- [ ] Clean up any deprecated environment variables from .env file
- [ ] Verify ocr_routing.json exists in pdf-ocr/tool/
- [ ] Add models to config as needed
- [ ] Test with current model setup
- [ ] Verify correct routing behavior for each model
