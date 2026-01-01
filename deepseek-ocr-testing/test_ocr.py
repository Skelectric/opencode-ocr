from vllm import LLM, SamplingParams
from vllm.model_executor.models.deepseek_ocr import NGramPerReqLogitsProcessor
from PIL import Image


def main():
    llm = LLM(
        model="unsloth/DeepSeek-OCR",
        enable_prefix_caching=False,
        mm_processor_cache_gb=0,
        logits_processors=[NGramPerReqLogitsProcessor],
        gpu_memory_utilization=0.15,
    )

    image = Image.open("test_image.png").convert("RGB")
    prompt = "<image>\nFree OCR."

    model_input = [{"prompt": prompt, "multi_modal_data": {"image": image}}]

    sampling_param = SamplingParams(
        temperature=0.0,
        max_tokens=8192,
        extra_args=dict(
            ngram_size=30,
            window_size=90,
            whitelist_token_ids={128821, 128822},
        ),
        skip_special_tokens=False,
    )

    model_outputs = llm.generate(model_input, sampling_param)
    for output in model_outputs:
        print(output.outputs[0].text)


if __name__ == "__main__":
    main()
