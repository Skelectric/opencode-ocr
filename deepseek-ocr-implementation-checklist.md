# DeepSeek-OCR PDF Tool Implementation Checklist

## Phase 1: Create Tool in Repository

### 1.1 Repository Structure Setup
- [x] Create repository directory: `~/opencode-ocr/pdf-ocr/tool/`
- [x] Create repository directory: `~/opencode-ocr/pdf-ocr/tool/`
- [x] Verify directory structure is correct

### 1.2 Create TypeScript Tool Definition
- [x] Create `~/opencode-ocr/pdf-ocr/tool/pdf-ocr.ts`
- [x] Import tool from @opencode-ai/plugin
- [x] Define tool description
- [x] Define pdf_path argument as string schema
- [x] Define output_format argument as string schema with default "markdown"
- [x] Implement execute function using `uv run`
- [x] Configure Bun.$ to call Python backend with pdf_path and output_format arguments
- [x] Return trimmed result from Python backend
- [x] Set execute default output_format to "markdown"
- [x] Note: Update path when deploying to `~/.config/opencode/tool/`

### 1.3 Create Python Backend Script
- [x] Create `~/opencode-ocr/pdf-ocr/tool/pdf_ocr_backend.py`
- [x] Add shebang line `#!/usr/bin/env python3`
- [x] Import sys module
- [x] Import fitz (PyMuPDF) for PDF handling
- [x] Import OpenAI client from openai library
- [x] Import Path from pathlib
- [x] Import base64 module
- [x] Import io module
- [x] Define main() function
- [x] Parse pdf_path from sys.argv[1]
- [x] Parse output_format from sys.argv[2] with default to 'markdown'
- [x] Validate PDF file exists using Path.exists()
- [x] Print error message and exit with code 1 if PDF not found
- [x] Validate PDF is readable by attempting to open it
- [x] Print error message and exit with code 1 if PDF is corrupt
- [x] Initialize OpenAI client with api_key="EMPTY"
- [x] Configure base_url to "http://localhost:8080/v1"
- [x] Configure timeout to 3600 seconds
- [x] Open PDF document using fitz.open()
- [x] Initialize empty results list
- [x] Loop through all pages using range(doc.page_count)
- [x] Convert each page to image using page.get_pixmap(dpi=144)
- [x] Convert pixmap to PNG bytes
- [x] Encode image bytes to base64
- [x] Prepare OCR request with image data URL
- [x] Set prompt to "Free OCR."
- [x] Configure max_tokens to 8192
- [x] Configure temperature to 0.0
- [x] Configure extra_body with skip_special_tokens=False
- [x] Configure vllm_xargs with ngram_size=30
- [x] Configure vllm_xargs with window_size=90
- [x] Configure vllm_xargs with whitelist_token_ids=[128821, 128822]
- [x] Send OCR request using client.chat.completions.create()
- [x] Extract OCR response text
- [x] Append page number prefix to result
- [x] Append result to results list
- [x] Join results with "\n\n" separator
- [x] Print final output
- [x] Close PDF document
- [x] Add try-except block for error handling
- [x] Catch and print error messages
- [x] Exit with code 1 on any exception
- [x] Add if __name__ == "__main__": main() entry point
- [x] Make Python script executable with chmod +x
- [x] Verify PDF conversion logic is implemented correctly
- [x] Verify image quality settings are applied (144 DPI, PNG, RGB)
- [x] Verify temporary image cleanup is implemented after processing
- [x] Verify sequential page processing to avoid memory issues

### 1.4 Create pyproject.toml
- [x] Create `~/opencode-ocr/pdf-ocr/pyproject.toml`
- [x] Define project metadata (name, version, description)
- [x] Set requires-python to ">=3.10"
- [x] Add openai dependency with version constraint
- [x] Add PyMuPDF dependency with version constraint
- [x] Add Pillow dependency with version constraint
- [x] Verify dependencies are correctly specified

### 1.5 Install Python Dependencies with uv
- [x] Navigate to `~/opencode-ocr/pdf-ocr/`
- [x] Run `uv sync` to install dependencies
- [x] Verify uv.lock file is created
- [x] Verify all packages are installed successfully
- [x] Test running backend with `uv run pdf_ocr_backend.py --help` or similar

### 1.6 Verify Tool Registration (after deployment)
- [ ] Deploy tool to `~/.config/opencode/tool/` when ready for testing
- [ ] Copy `pdf-ocr.ts` to `~/.config/opencode/tool/`
- [ ] Copy `pdf_ocr_backend.py` to `~/.config/opencode/tool/`
- [ ] Copy `pyproject.toml` to `~/.config/opencode/tool/`
- [ ] Run `uv sync` in deployment directory
- [ ] Run `opencode tools` command
- [ ] Confirm pdf-ocr tool appears in tool list
- [ ] Verify tool description is visible

## Phase 2: Testing & Validation

### 2.0 Deploy for Testing
- [x] Create deployment directory: `mkdir -p ~/.config/opencode/tool/`
- [x] Copy `pdf-ocr.ts` from repository to deployment directory
- [x] Copy `pdf_ocr_backend.py` from repository to deployment directory
- [x] Copy `pyproject.toml` from repository to deployment directory
- [x] Run `uv sync` in deployment directory to install dependencies
- [x] Update execute path in pdf-ocr.ts if needed for deployment

### 2.1 Prepare Test Environment
- [x] Navigate to `~/opencode-ocr/deepseek-ocr-testing/` directory
- [x] Identify test PDF files
- [x] Verify test files are accessible
- [x] Create test environment verification script
- [x] Run test environment verification tests

### 2.2 Test Case 1: Simple Single-Page PDF
- [x] Locate a simple single-page test PDF
- [x] Verify PDF-to-image conversion completes successfully
- [x] Verify image quality is sufficient for OCR (check DPI, format, color space)
- [x] Run pdf-ocr tool with markdown output format
- [x] Verify basic text extraction works
- [x] Verify markdown formatting is correct
- [x] Confirm no errors occurred
- [x] Verify temporary images are cleaned up after processing
- [x] Run pdf-ocr tool with plain text output format
- [x] Verify plain text output is correct
- [x] Compare markdown and text outputs

### 2.3 Test Case 2: Multi-Page Document
- [x] Locate a multi-page test PDF
- [x] Verify all PDF pages convert to images successfully
- [x] Verify each page image is processed with OCR
- [x] Run pdf-ocr tool with markdown output format
- [x] Verify all pages are processed
- [x] Verify page concatenation is correct
- [x] Verify page break markers are present
- [x] Verify consistent formatting across pages
- [x] Count total pages in output
- [x] Verify page count matches PDF page count

## Phase 3: Deployment

### 3.2 Prepare Deployment on miniPC
- [x] Create tool directory on miniPC: `mkdir -p ~/.config/opencode/tool/`
- [ ] Copy pdf-ocr.ts to miniPC tool directory
- [ ] Copy pdf_ocr_backend.py to miniPC tool directory
- [ ] Copy pyproject.toml to miniPC tool directory
- [ ] Run `uv sync` in miniPC tool directory
- [ ] Test tool with sample PDF on miniPC
- [ ] Verify tool works correctly on miniPC

## Phase 4: Documentation & Maintenance

### 4.1 Verify Tool Documentation
- [x] Review tool description in pdf-ocr.ts
- [x] Confirm description clearly states tool purpose
- [x] Confirm description mentions markdown and text output formats
- [x] Confirm description indicates when to use the tool
- [x] Verify no AGENTS.md modifications are needed
- [x] Test that tool description is automatically available to agents
- [x] Document that Python scripts should be run with `uv run`

### 4.2 Create Deployment Script
- [x] Create deploy-tool.sh script (combines installation and update)
- [x] Make script executable with chmod +x
- [x] Add error handling and validation to script
- [x] Support --force flag for reinstallation
- [x] Support --repo flag for custom repository path
- [x] Auto-detect installation status (install vs update)
- [x] Create test_deploy_script.py unit tests
- [x] Update test_documentation.py to include deployment script tests
- [x] Run tests and verify script works correctly
- [x] Update README.md with deployment script documentation
- [x] Verify pre-commit checks pass for all script files
- [x] Combine install-tool.sh and update-tool.sh into single deploy-tool.sh
- [x] Remove old installation script files
- [x] Remove [project.scripts] from pyproject.toml to fix uv sync warning
- [x] Fix verification step in deploy-tool.sh (remove invalid opencode tools command)
- [x] Test deployment script successfully

### 4.3 Future Enhancement Planning
- [ ] Document partial page range support as future enhancement

