#!/usr/bin/env python3
"""
Test environment verification for PDF OCR testing.

Verifies that test PDF files are accessible and ready for testing.
"""

import sys
import fitz
from pathlib import Path


def test_single_page_pdf():
    """Test that single-page PDF is accessible."""
    print("Testing single-page PDF accessibility...")

    test_pdf = Path("/home/ubuntu/opencode-ocr/pdf-ocr/test-single-page.pdf")

    if not test_pdf.exists():
        print(f"✗ Single-page PDF not found: {test_pdf}")
        return False

    try:
        doc = fitz.open(str(test_pdf))
        assert doc.page_count == 1, "PDF should have 1 page"
        assert doc.is_pdf, "File should be a valid PDF"
        doc.close()
        print(f"✓ Single-page PDF is accessible: {test_pdf}")
        return True
    except Exception as e:
        print(f"✗ Single-page PDF test failed: {e}")
        return False


def test_multipage_pdf():
    """Test that multi-page PDF is accessible."""
    print("Testing multi-page PDF accessibility...")

    test_pdf = Path("/home/ubuntu/opencode-ocr/pdf-ocr/multipage.pdf")

    if not test_pdf.exists():
        print(f"✗ Multi-page PDF not found: {test_pdf}")
        return False

    try:
        doc = fitz.open(str(test_pdf))
        assert doc.page_count == 10, "PDF should have 10 pages"
        assert doc.is_pdf, "File should be a valid PDF"
        doc.close()
        print(f"✓ Multi-page PDF is accessible: {test_pdf}")
        return True
    except Exception as e:
        print(f"✗ Multi-page PDF test failed: {e}")
        return False


def test_bank_statement_image():
    """Test that bank statement image is accessible."""
    print("Testing bank statement image accessibility...")

    test_image = Path(
        "/home/ubuntu/opencode-ocr/deepseek-ocr-testing/bank-statement-template-09.jpg"
    )

    if not test_image.exists():
        print(f"✗ Bank statement image not found: {test_image}")
        return False

    try:
        size = test_image.stat().st_size
        assert size > 0, "Image file should not be empty"
        print(
            f"✓ Bank statement image is accessible: {test_image} ({size / 1024:.1f} KB)"
        )
        return True
    except Exception as e:
        print(f"✗ Bank statement image test failed: {e}")
        return False


def main():
    """Run all test environment verification tests."""
    print("\n=== Test Environment Verification ===\n")

    results = [
        test_single_page_pdf(),
        test_multipage_pdf(),
        test_bank_statement_image(),
    ]

    print("\n=== Test Environment Summary ===")
    print(f"Total tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")

    if all(results):
        print("\n✓ All test files are accessible and ready for testing.")
        return 0
    else:
        print("\n✗ Some test files are missing or inaccessible.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
