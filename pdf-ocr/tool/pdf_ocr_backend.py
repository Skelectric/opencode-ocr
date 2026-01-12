#!/usr/bin/env python3
import sys
import os
import fitz
from openai import OpenAI
from pathlib import Path
import base64
import argparse


def main():
    parser = argparse.ArgumentParser(description="Process PDF using DeepSeek-OCR")
    parser.add_argument("pdf_path", help="Absolute path to PDF file")
    parser.add_argument(
        "output_format",
        nargs="?",
        default="markdown",
        choices=["markdown", "text"],
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--base-url",
        help="OpenAI-compatible endpoint URL (overrides DEEPSEEK_OCR_BASE_URL env var)",
    )
    args = parser.parse_args()

    pdf_path = args.pdf_path

    if not Path(pdf_path).exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    doc = None
    try:
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            print("Error: PDF has no pages")
            sys.exit(1)
    except Exception as e:
        print(f"Error: Could not open PDF file: {e}")
        sys.exit(1)

    base_url = args.base_url or os.getenv("DEEPSEEK_OCR_BASE_URL")
    if not base_url:
        print("Error: DEEPSEEK_OCR_BASE_URL not set. Set it via:")
        print(
            "  1. Environment variable: export DEEPSEEK_OCR_BASE_URL='http://your-endpoint:8080/v1'"
        )
        print(
            "  2. .env file: Add DEEPSEEK_OCR_BASE_URL='http://your-endpoint:8080/v1' to .env"
        )
        print("  3. CLI argument: --base-url http://your-endpoint:8080/v1")
        sys.exit(1)
    client = OpenAI(api_key="EMPTY", base_url=base_url, timeout=3600)

    results = []

    try:
        for page_num in range(doc.page_count):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=144, colorspace=fitz.csRGB)
            img_bytes = pix.tobytes("png")
            pix = None
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            img_data_url = f"data:image/png;base64,{img_base64}"

            response = client.chat.completions.create(
                model="deepseek-ocr",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": img_data_url}},
                            {"type": "text", "text": "Free OCR."},
                        ],
                    }
                ],
                temperature=0.0,
                extra_body={
                    "skip_special_tokens": False,
                    "vllm_xargs": {
                        "ngram_size": 30,
                        "window_size": 90,
                        "whitelist_token_ids": [128821, 128822],
                    },
                },
            )

            if not response.choices or len(response.choices) == 0:
                print(f"Error: No OCR response for page {page_num + 1}")
                sys.exit(1)

            result_text = response.choices[0].message.content
            results.append(f"--- Page {page_num + 1} ---\n{result_text}")

            img_data_url = None
            img_base64 = None

        output = "\n\n".join(results)
        print(output)

    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)
    finally:
        if doc is not None:
            doc.close()


if __name__ == "__main__":
    main()
