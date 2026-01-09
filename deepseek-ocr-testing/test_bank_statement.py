#!/usr/bin/env python3
import time
from pathlib import Path
from openai import OpenAI


def main():
    client = OpenAI(api_key="EMPTY", base_url="http://localhost:8080/v1", timeout=3600)

    script_dir = Path(__file__).parent
    image_path = script_dir / "bank-statement-template-09.jpg"
    image_url = f"file://{image_path.absolute()}"

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
                {
                    "type": "text",
                    "text": "<|grounding|>Convert the document to markdown.",
                },
            ],
        }
    ]

    print("Sending bank statement OCR request to llama-swap...")
    start = time.time()

    response = client.chat.completions.create(
        model="deepseek-ocr",
        messages=messages,
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

    elapsed = time.time() - start
    print(f"Response time: {elapsed:.2f}s")

    text = response.choices[0].message.content
    print(f"Generated text:\n{text}")

    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "bank-statement-ocr.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"\nOutput saved to: {output_file}")


if __name__ == "__main__":
    main()
