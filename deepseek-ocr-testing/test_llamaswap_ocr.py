#!/usr/bin/env python3
import time
import os
from pathlib import Path
from openai import OpenAI


def main():
    client = OpenAI(api_key="EMPTY", base_url="http://localhost:8080/v1", timeout=3600)

    script_dir = Path(__file__).parent
    image_path = script_dir / "test_image.png"
    image_url = f"file://{image_path.absolute()}"

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
                {"type": "text", "text": "Free OCR."},
            ],
        }
    ]

    print("Sending OCR request to llama-swap...")
    start = time.time()

    response = client.chat.completions.create(
        model="deepseek-ocr",
        messages=messages,
        max_tokens=2048,
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
    print(f"Generated text:\n{response.choices[0].message.content}")


if __name__ == "__main__":
    main()
