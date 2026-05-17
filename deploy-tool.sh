#!/usr/bin/env bash
set -euo pipefail

# Installation/Update script for DeepSeek-OCR PDF Tool
# Usage: ./deploy-tool.sh [options]
# Options:
#   --force    Force reinstallation even if already installed
#   --repo <path>  Specify custom repository path (default: ~/opencode-ocr)

REPO_DIR="."
TOOL_DIR="$HOME/.config/opencode/tool"
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --repo)
            REPO_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--force] [--repo <path>]"
            exit 1
            ;;
    esac
done

# Check if source exists
if [ ! -d "$REPO_DIR" ]; then
    echo "Error: Repository not found at $REPO_DIR"
    echo "Please clone the repository first or provide a valid path with --repo"
    exit 1
fi

# Check if already installed
if [ -f "$TOOL_DIR/pdf-ocr.ts" ] && [ "$FORCE" = false ]; then
    echo "Tool already installed. Updating..."
    ACTION="updating"
else
    echo "Installing DeepSeek-OCR PDF Tool..."
    ACTION="installing"
fi

echo "Source: $REPO_DIR"
echo "Target: $TOOL_DIR"
echo "Action: $ACTION"

# Pull latest changes if it's a git repo
if [ -d "$REPO_DIR/.git" ]; then
    echo "Pulling latest changes..."
    cd "$REPO_DIR"
    git pull || echo "Warning: git pull failed, continuing with current state"
fi

# Create tool directory if it doesn't exist
mkdir -p "$TOOL_DIR"

# Copy tool files
echo "Copying tool files..."
cp "$REPO_DIR/pdf-ocr/tool/pdf-ocr.ts" "$TOOL_DIR/"
cp "$REPO_DIR/pdf-ocr/tool/pdf_ocr_backend.py" "$TOOL_DIR/"
cp "$REPO_DIR/pdf-ocr/pyproject.toml" "$TOOL_DIR/"

# Copy example routing config as reference (never overwrite user config)
if [ ! -f "$TOOL_DIR/ocr_routing.json.example" ]; then
    cp "$REPO_DIR/pdf-ocr/tool/ocr_routing.json.example" "$TOOL_DIR/"
fi

# Make Python script executable
chmod +x "$TOOL_DIR/pdf_ocr_backend.py"

# Check if .env file exists, if not prompt for configuration
ENV_FILE="$TOOL_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "No .env file found. Please provide configuration."
    echo ""
    echo "This tool requires a llama-swap proxy endpoint that provides:"
    echo "  - DeepSeek-OCR model serving"
    echo "  - Model status endpoint (/running)"
    echo "  - Model capability checks (/upstream/{model}/props)"
    echo ""
    
    # Prompt for llama-swap endpoint
    read -p "Enter llama-swap endpoint URL (e.g., http://localhost:8080): " ENDPOINT
    
    if [ -z "$ENDPOINT" ]; then
        echo "Warning: No endpoint provided. Creating .env using default."
        ENDPOINT="http://localhost:8080"
    fi
    
    echo "DEEPSEEK_OCR_BASE_URL=\"$ENDPOINT\"" > "$ENV_FILE"
    
    echo ".env file created at $ENV_FILE"
    
    # Create OCR routing configuration
    ROUTING_CONFIG="$TOOL_DIR/ocr_routing.json"
    if [ ! -f "$ROUTING_CONFIG" ]; then
        echo ""
        echo "Creating OCR routing configuration..."
        echo "This file maps loaded model sets to their preferred OCR method."
        echo "Single-model keys work as before. Comma-separated keys match ALL loaded models."
        
        cat > "$ROUTING_CONFIG" << 'EOF'
{
  "_comment": "OCR Routing Configuration - Maps loaded model sets to preferred OCR method. Single-model keys work as before. Comma-separated keys match ALL loaded models (order-independent).",
  "_routing_options": {
    "deepseek-ocr": "Use DeepSeek-OCR model (requires sufficient VRAM)",
    "deepseek-ocr-2": "Use DeepSeek-OCR-2 model (requires sufficient VRAM)",
    "glm-ocr": "Use GLM-OCR model (lighter VRAM, for constrained setups)",
    "current_model": "Use the currently loaded model (requires vision support)"
  },
  "ocr_routing": {
    "_comment": "Model-set examples: comma-separated keys match ALL loaded models",
    "kimi-k2.6,qwen3.6-35b-a3b-nvfp4": "deepseek-ocr-2",
    "kimi-k2.6,qwen3.6-27b-nvfp4": "glm-ocr",
    "kimi-k2.6": "current_model"
  },
  "default": "current_model"
}
EOF
        
        echo "Created default routing config at $ROUTING_CONFIG"
        echo "Edit this file to enable DeepSeek-OCR for specific models."
    fi
else
    echo ".env file already exists at $ENV_FILE"
    # During updates, remind users about the example config
    if [ -f "$TOOL_DIR/ocr_routing.json.example" ]; then
        echo "Reference config with model-set routing examples: $TOOL_DIR/ocr_routing.json.example"
    fi
fi

# Install/update Python dependencies
echo "Installing Python dependencies..."
cd "$TOOL_DIR"
uv sync

# Verify installation
echo "Verifying installation..."
if [ -f "$TOOL_DIR/pdf-ocr.ts" ] && [ -f "$TOOL_DIR/pdf_ocr_backend.py" ] && [ -f "$TOOL_DIR/pyproject.toml" ]; then
    echo "All tool files installed successfully"
else
    echo "Warning: Some tool files may be missing"
fi

echo ""
if [ "$ACTION" = "updating" ]; then
    echo "Update complete!"
    echo "Tool files have been updated in $TOOL_DIR"
    echo "You may need to restart your opencode session for changes to take effect."
else
    echo "Installation complete!"
    echo "Tool files are in $TOOL_DIR"
    echo "To update the tool later, run: ./deploy-tool.sh"
fi
