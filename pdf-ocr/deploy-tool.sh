#!/bin/bash
set -euo pipefail

# Installation/Update script for DeepSeek-OCR PDF Tool
# Usage: ./deploy-tool.sh [options]
# Options:
#   --force    Force reinstallation even if already installed
#   --repo <path>  Specify custom repository path (default: ~/opencode-ocr)

REPO_DIR="$HOME/opencode-ocr"
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

# Make Python script executable
chmod +x "$TOOL_DIR/pdf_ocr_backend.py"

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
