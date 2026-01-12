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
- [ ] Verify PDF conversion logic is implemented correctly
- [ ] Verify image quality settings are applied (144 DPI, PNG, RGB)
- [ ] Verify temporary image cleanup is implemented after processing
- [ ] Verify sequential page processing to avoid memory issues

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
- [ ] Navigate to `~/opencode-ocr/deepseek-ocr-testing/` directory
- [ ] Identify test PDF files
- [ ] Verify test files are accessible

### 2.2 Test Case 1: Simple Single-Page PDF
- [ ] Locate a simple single-page test PDF
- [ ] Verify PDF-to-image conversion completes successfully
- [ ] Verify image quality is sufficient for OCR (check DPI, format, color space)
- [ ] Run pdf-ocr tool with markdown output format
- [ ] Verify basic text extraction works
- [ ] Verify markdown formatting is correct
- [ ] Confirm no errors occurred
- [ ] Verify temporary images are cleaned up after processing
- [ ] Run pdf-ocr tool with plain text output format
- [ ] Verify plain text output is correct
- [ ] Compare markdown and text outputs

### 2.3 Test Case 2: Multi-Page Document
- [ ] Locate a multi-page test PDF
- [ ] Verify all PDF pages convert to images successfully
- [ ] Verify each page image is processed with OCR
- [ ] Run pdf-ocr tool with markdown output format
- [ ] Verify all pages are processed
- [ ] Verify page concatenation is correct
- [ ] Verify page break markers are present
- [ ] Verify consistent formatting across pages
- [ ] Count total pages in output
- [ ] Verify page count matches PDF page count
- [ ] Verify no memory leaks occur during multi-page processing

### 2.4 Test Case 3: Complex Layout (Bank Statement)
- [ ] Locate bank statement template PDF
- [ ] Run pdf-ocr tool with markdown output format
- [ ] Verify table extraction works
- [ ] Verify column structure is preserved
- [ ] Verify numeric data accuracy
- [ ] Compare OCR output with known values
- [ ] Verify table markdown formatting is correct

### 2.5 Test Case 4: Large PDF (>10 pages)
- [ ] Locate or create a large PDF test file (>10 pages)
- [ ] Verify all pages convert to images without memory issues
- [ ] Run pdf-ocr tool with markdown output format
- [ ] Monitor memory usage during PDF conversion phase
- [ ] Monitor memory usage during OCR processing phase
- [ ] Record processing time per page
- [ ] Record total processing time
- [ ] Verify complete output is returned
- [ ] Verify no memory leaks occurred
- [ ] Verify all pages were processed
- [ ] Verify temporary images are cleaned up after each page or at end

### 2.6 Test Case 5: Error Scenarios
- [ ] Test with non-existent PDF file path
- [ ] Verify appropriate error message is shown
- [ ] Verify exit code is 1
- [ ] Test with corrupt or invalid PDF file
- [ ] Verify error message indicates corrupt file
- [ ] Verify exit code is 1
- [ ] Test with unreadable PDF file (no permissions)
- [ ] Verify error message is shown
- [ ] Verify exit code is 1
- [ ] Stop llama-swap service and test OCR request
- [ ] Verify timeout or connection error is handled
- [ ] Verify error message indicates service unavailable
- [ ] Restart llama-swap service

### 2.7 Performance Metrics Collection
- [ ] Record PDF-to-image conversion time for single-page PDF
- [ ] Record OCR processing time for single-page PDF
- [ ] Record total processing time for single-page PDF
- [ ] Record PDF-to-image conversion time for multi-page PDF
- [ ] Record OCR processing time for multi-page PDF
- [ ] Record total processing time for multi-page PDF
- [ ] Calculate average processing time per page (including conversion)
- [ ] Monitor VRAM usage during PDF conversion
- [ ] Monitor VRAM usage during OCR processing
- [ ] Record peak VRAM usage
- [ ] Verify VRAM usage is stable throughout
- [ ] Record memory usage statistics for conversion phase
- [ ] Record memory usage statistics for OCR phase
- [ ] Compare processing times against benchmarks (<30 seconds per page)

### 2.8 Quality Verification
- [ ] Manually review OCR output for accuracy
- [ ] Verify OCR accuracy exceeds 95% for test documents
- [ ] Check for any data loss or corruption
- [ ] Verify table structures are preserved
- [ ] Verify numeric values are correct
- [ ] Verify text formatting is maintained

## Phase 3: Multi-System Deployment

### 3.1 Prepare Deployment on llmrig
- [ ] Verify tool directory exists: `~/.config/opencode/tool/`
- [ ] Verify pdf-ocr.ts exists in tool directory
- [ ] Verify pdf_ocr_backend.py exists in tool directory
- [ ] Verify Python dependencies are installed
- [ ] Run `opencode tools` to verify tool is registered
- [ ] Test tool with sample PDF on llmrig
- [ ] Verify llama-swap endpoint is accessible at http://localhost:8080/v1
- [ ] Verify deepseek-ocr model is loaded
- [ ] Confirm tool works correctly on llmrig

### 3.2 Prepare Deployment on miniPC
- [ ] Create tool directory on miniPC: `mkdir -p ~/.config/opencode/tool/`
- [ ] Copy pdf-ocr.ts to miniPC tool directory
- [ ] Copy pdf_ocr_backend.py to miniPC tool directory
- [ ] Copy pyproject.toml to miniPC tool directory
- [ ] Run `uv sync` in miniPC tool directory
- [ ] Verify llmrig hostname resolves on miniPC
- [ ] Check /etc/hosts for llmrig entry (192.168.104.222)
- [ ] Add llmrig to /etc/hosts if missing: `echo "192.168.104.222 llmrig" | sudo tee -a /etc/hosts`
- [ ] Test network connectivity to llmrig: `ping llmrig`
- [ ] Test HTTP connectivity to llama-swap: `curl http://llmrig:8080/v1/models`
- [ ] Run `opencode tools` on miniPC to verify tool registration
- [ ] Test tool with sample PDF on miniPC
- [ ] Verify tool works correctly on miniPC
- [ ] Compare results with llmrig results

### 3.3 Prepare Deployment on DESKTOP-V4ETCL4
- [ ] Create tool directory on DESKTOP-V4ETCL4: `mkdir -p ~/.config/opencode/tool/`
- [ ] Copy pdf-ocr.ts to DESKTOP-V4ETCL4 tool directory
- [ ] Copy pdf_ocr_backend.py to DESKTOP-V4ETCL4 tool directory
- [ ] Copy pyproject.toml to DESKTOP-V4ETCL4 tool directory
- [ ] Run `uv sync` in DESKTOP-V4ETCL4 tool directory
- [ ] Verify llmrig hostname resolves on DESKTOP-V4ETCL4
- [ ] Check /etc/hosts for llmrig entry (192.168.104.222)
- [ ] Add llmrig to /etc/hosts if missing: `echo "192.168.104.222 llmrig" | sudo tee -a /etc/hosts`
- [ ] Test network connectivity to llmrig: `ping llmrig`
- [ ] Test HTTP connectivity to llama-swap: `curl http://llmrig:8080/v1/models`
- [ ] Run `opencode tools` on DESKTOP-V4ETCL4 to verify tool registration
- [ ] Test tool with sample PDF on DESKTOP-V4ETCL4
- [ ] Verify tool works correctly on DESKTOP-V4ETCL4
- [ ] Compare results with llmrig results

### 3.4 Firewall Configuration (llmrig)
- [ ] Check firewall rules on llmrig for port 8080
- [ ] Verify port 8080 is accessible from miniPC
- [ ] Verify port 8080 is accessible from DESKTOP-V4ETCL4
- [ ] Add firewall rule if needed to allow traffic from miniPC
- [ ] Add firewall rule if needed to allow traffic from DESKTOP-V4ETCL4
- [ ] Reload firewall configuration if changes were made
- [ ] Test connectivity from miniPC to llmrig port 8080
- [ ] Test connectivity from DESKTOP-V4ETCL4 to llmrig port 8080

### 3.5 Cross-System Testing
- [ ] Run identical test PDF on all three systems
- [ ] Compare outputs from llmrig, miniPC, and DESKTOP-V4ETCL4
- [ ] Verify outputs are identical across all systems
- [ ] Test with different PDF types on each system
- [ ] Verify consistent behavior across all systems
- [ ] Measure latency differences between systems
- [ ] Document any performance variations

## Phase 4: Documentation & Maintenance

### 4.1 Verify Tool Documentation
- [ ] Review tool description in pdf-ocr.ts
- [ ] Confirm description clearly states tool purpose
- [ ] Confirm description mentions markdown and text output formats
- [ ] Confirm description indicates when to use the tool
- [ ] Verify no AGENTS.md modifications are needed
- [ ] Test that tool description is automatically available to agents
- [ ] Document that Python scripts should be run with `uv run`

### 4.2 Create Usage Examples
- [ ] Document basic markdown output usage example
- [ ] Document plain text output usage example
- [ ] Document error handling scenarios
- [ ] Document typical processing times
- [ ] Document system requirements
- [ ] Document network requirements for remote systems
- [ ] Document uv run usage for Python scripts

### 4.3 Maintenance Tasks Setup
- [ ] Set up llama-swap service monitoring
- [ ] Configure alerts for service downtime
- [ ] Document dependency update process (update pyproject.toml, run uv sync)
- [ ] Document tool update process
- [ ] Create log file for tool usage tracking
- [ ] Set up periodic OCR accuracy verification
- [ ] Document troubleshooting steps for common issues

### 4.4 Future Enhancement Planning
- [ ] Document partial page range support as future enhancement
- [ ] Document batch processing support as future enhancement
- [ ] Document progress reporting as future enhancement
- [ ] Document additional output formats as future enhancement
- [ ] Document caching mechanism as future enhancement

## Success Criteria Verification

### Functional Requirements
- [ ] Tool successfully processes PDF files on all systems
- [ ] Tool returns markdown output correctly
- [ ] Tool returns plain text output correctly
- [ ] Tool handles multi-page documents correctly
- [ ] Tool implements fail-fast error handling
- [ ] Tool works on llmrig
- [ ] Tool works on miniPC
- [ ] Tool works on DESKTOP-V4ETCL4

### Performance Requirements
- [ ] Processing time is less than 30 seconds per page
- [ ] Memory usage remains stable during processing
- [ ] No memory leaks detected
- [ ] Network latency is acceptable on miniPC
- [ ] Network latency is acceptable on DESKTOP-V4ETCL4
- [ ] Total processing time for large PDFs is reasonable

### Quality Requirements
- [ ] OCR accuracy exceeds 95% on test documents
- [ ] Table structures are preserved in output
- [ ] Numeric data is accurately extracted
- [ ] No data loss occurs during processing
- [ ] No data corruption occurs during processing
- [ ] Output formatting is consistent

## Final Validation

- [ ] Run comprehensive test suite on all systems
- [ ] Verify all test cases pass
- [ ] Verify all error scenarios are handled correctly
- [ ] Document any issues found
- [ ] Resolve all documented issues
- [ ] Re-run test suite after fixes
- [ ] Confirm all systems are operational
- [ ] Confirm tool is ready for production use

---

**Checklist Version**: 1.0
**Created**: January 12, 2026
**Based on**: deepseek-ocr-tool-implementation-plan.md v1.0
