#!/usr/bin/env python3
"""Test deployment script."""

import subprocess
import sys
from pathlib import Path


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


def test_deploy_script_help():
    """Verify deploy-tool.sh can display usage information."""
    deploy_script = Path(__file__).parent / "deploy-tool.sh"

    try:
        # Test with invalid option to trigger usage message
        result = subprocess.run(
            ["bash", str(deploy_script), "--invalid-option"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("FAIL: deploy-tool.sh should exit with error for invalid option")
            return False
        if "Usage:" not in result.stderr:
            print("FAIL: deploy-tool.sh should display usage information")
            return False
        print("PASS: deploy-tool.sh displays usage information correctly")
        return True
    except Exception as e:
        print(f"FAIL: Exception testing help: {e}")
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
    """Run all deployment script tests."""
    print("Testing deployment script...\n")

    tests = [
        ("Deploy script exists", test_deploy_script_exists),
        ("Deploy script syntax", test_deploy_script_syntax),
        ("Deploy script help", test_deploy_script_help),
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
