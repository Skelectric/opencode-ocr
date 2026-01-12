#!/usr/bin/env python3
"""Test script to verify tool description and documentation."""

import subprocess
import sys
from pathlib import Path


def test_tool_description():
    """Verify tool description meets requirements."""
    tool_file = Path(__file__).parent / "tool" / "pdf-ocr.ts"

    if not tool_file.exists():
        print("FAIL: Tool file not found")
        return False

    content = tool_file.read_text()

    requirements = {
        "purpose": "Extract text from PDF files using DeepSeek-OCR",
        "formats": "markdown or plain text",
        "usage": "Use this when you need to transcribe",
    }

    for name, phrase in requirements.items():
        if phrase not in content:
            print(f"FAIL: Missing {name} in tool description")
            return False
        print(f"PASS: {name} found in tool description")

    return True


def test_documentation_exists():
    """Verify README.md exists and contains key information."""
    readme = Path(__file__).parent / "README.md"

    if not readme.exists():
        print("FAIL: README.md not found")
        return False

    content = readme.read_text()

    required_sections = [
        "# DeepSeek-OCR PDF Tool",
        "## Installation",
        "## Usage",
        "uv run",
        "## Parameters",
        "deploy-tool.sh",
    ]

    for section in required_sections:
        if section not in content:
            print(f"FAIL: Missing section: {section}")
            return False
        print(f"PASS: Section '{section}' found in README.md")

    return True


def test_deploy_script_exists():
    """Verify deploy-tool.sh exists and is executable."""
    deploy_script = Path(__file__).parent / "deploy-tool.sh"

    if not deploy_script.exists():
        print("FAIL: deploy-tool.sh not found")
        return False

    if not deploy_script.stat().st_mode & 0o111:
        print("FAIL: deploy-tool.sh is not executable")
        return False

    print("PASS: deploy-tool.sh exists and is executable")
    return True


def test_deploy_script_syntax():
    """Verify deploy-tool.sh has valid bash syntax."""
    deploy_script = Path(__file__).parent / "deploy-tool.sh"

    try:
        result = subprocess.run(
            ["bash", "-n", str(deploy_script)], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"FAIL: deploy-tool.sh syntax error: {result.stderr}")
            return False
        print("PASS: deploy-tool.sh has valid bash syntax")
        return True
    except Exception as e:
        print(f"FAIL: Exception checking syntax: {e}")
        return False


def test_pyproject_no_scripts():
    """Verify pyproject.toml does not have project.scripts section."""
    pyproject = Path(__file__).parent / "pyproject.toml"

    if not pyproject.exists():
        print("FAIL: pyproject.toml not found")
        return False

    content = pyproject.read_text()

    if "[project.scripts]" in content:
        print("FAIL: pyproject.toml should not have [project.scripts] section")
        return False

    print("PASS: pyproject.toml correctly omits [project.scripts] section")
    return True


def main():
    """Run all documentation tests."""
    print("Testing tool documentation...\n")

    tests = [
        ("Tool description", test_tool_description),
        ("README documentation", test_documentation_exists),
        ("Deploy script exists", test_deploy_script_exists),
        ("Deploy script syntax", test_deploy_script_syntax),
        ("pyproject.toml configuration", test_pyproject_no_scripts),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n--- Testing {name} ---")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"FAIL: Exception during test: {e}")
            results.append((name, False))

    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)

    all_passed = True
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{name}: {status}")
        if not result:
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
