#!/usr/bin/env python3
import sys
import fitz
from openai import OpenAI
from pathlib import Path
import base64


def main():
    pdf_path = sys.argv[1]

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

    client = OpenAI(
        api_key="EMPTY", base_url="http://192.168.104.222:8080/v1", timeout=3600
    )

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
