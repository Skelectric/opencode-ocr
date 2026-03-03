#!/usr/bin/env python3
import sys
import os
import subprocess
from typing import Tuple, Optional
import fitz
from openai import OpenAI
from pathlib import Path
import base64
import argparse
from dotenv import load_dotenv
import logging
import requests

# Load environment variables from .env file in the tool directory
tool_dir = Path(__file__).parent
env_path = tool_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)


def validate_environment_variables():
    """Validate environment variables for configuration."""
    errors = []
    warnings = []

    # Validate PDF_OCR_VRAM_THRESHOLD_GB (optional, must be positive integer)
    vram_threshold = os.getenv("PDF_OCR_VRAM_THRESHOLD_GB")
    if vram_threshold:
        try:
            vram_value = int(vram_threshold)
            if vram_value <= 0:
                errors.append(
                    f"PDF_OCR_VRAM_THRESHOLD_GB must be a positive integer: {vram_threshold}"
                )
            elif vram_value < 10:
                warnings.append(
                    f"PDF_OCR_VRAM_THRESHOLD_GB is set to {vram_value} GB, which is quite low. "
                    "DeepSeek-OCR may not load properly with less than 10-17 GB."
                )
            elif vram_value > 48:
                warnings.append(
                    f"PDF_OCR_VRAM_THRESHOLD_GB is set to {vram_value} GB, which is quite high. "
                    "This may rarely allow DeepSeek-OCR to load."
                )
        except ValueError:
            errors.append(
                f"PDF_OCR_VRAM_THRESHOLD_GB must be a valid integer: {vram_threshold}"
            )

    # Validate DEEPSEEK_OCR_BASE_URL (required)
    deepseek_url = os.getenv("DEEPSEEK_OCR_BASE_URL")
    if deepseek_url and not deepseek_url.startswith(("http://", "https://")):
        errors.append(
            f"DEEPSEEK_OCR_BASE_URL must be a valid URL starting with http:// or https://: {deepseek_url}"
        )

    return errors, warnings


# Run validation on module load
_validation_errors, _validation_warnings = validate_environment_variables()

if _validation_warnings:
    for warning in _validation_warnings:
        print(f"Warning: {warning}", file=sys.stderr)

if _validation_errors:
    for error in _validation_errors:
        print(f"Configuration Error: {error}", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_vram_availability() -> Tuple[bool, int]:
    """
    Check if sufficient VRAM is available for DeepSeek-OCR.

    Returns:
        Tuple[bool, int]: (has_sufficient_vram, free_vram_mb)
        - has_sufficient_vram: True if VRAM check succeeded and has > 0 MB free
        - free_vram_mb: Total free VRAM in megabytes across all GPUs

    Raises:
        subprocess.CalledProcessError: If nvidia-smi command fails
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse output - each line represents one GPU
        free_memory_values = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    free_mb = int(line.strip())
                    free_memory_values.append(free_mb)
                except ValueError:
                    logger.warning(f"Could not parse VRAM value: {line}")
                    continue

        if not free_memory_values:
            logger.error("No VRAM values could be parsed from nvidia-smi output")
            return (False, 0)

        # Sum free VRAM across all GPUs
        total_free_mb = sum(free_memory_values)
        has_sufficient = total_free_mb > 0

        logger.info(
            f"VRAM Detection: Found {len(free_memory_values)} GPU(s), "
            f"Total free VRAM: {total_free_mb} MB ({total_free_mb / 1024:.2f} GB)"
        )

        return (has_sufficient, total_free_mb)

    except subprocess.CalledProcessError as e:
        logger.error(f"nvidia-smi command failed: {e}")
        logger.error(f"stderr: {e.stderr}")
        raise
    except FileNotFoundError:
        logger.error("nvidia-smi not found. Ensure NVIDIA drivers are installed.")
        raise
    except Exception as e:
        logger.error(f"Unexpected error checking VRAM: {e}")
        raise


def get_current_model(base_url: str) -> Optional[str]:
    """
    Query ik_llama.cpp /running endpoint for currently loaded model.

    Args:
        base_url: Base URL for the ik_llama.cpp endpoint

    Returns:
        Optional[str]: Model ID string if a model is loaded, None otherwise
    """
    try:
        url = f"{base_url}/running"
        logger.info(f"Querying current model from: {url}")

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Handle different response formats
        if isinstance(data, list) and len(data) > 0:
            # List format - extract model from first item
            model_id = data[0].get("model") or data[0].get("id")
            if model_id:
                logger.info(f"Current model detected: {model_id}")
                return model_id
        elif isinstance(data, dict):
            # Dict format: check for "running" key (llama-swap proxy)
            if (
                "running" in data
                and isinstance(data["running"], list)
                and len(data["running"]) > 0
            ):
                model_id = data["running"][0].get("model") or data["running"][0].get(
                    "id"
                )
                if model_id:
                    logger.info(f"Current model detected: {model_id}")
                    return model_id
            # Direct dict format - check for model field
            model_id = data.get("model") or data.get("id")
            if model_id:
                logger.info(f"Current model detected: {model_id}")
                return model_id

        logger.warning("No model currently loaded")
        return None

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection failed to {base_url}/running: {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout querying {base_url}/running")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None
    except (KeyError, ValueError) as e:
        logger.error(f"Failed to parse response: {e}")
        return None


def check_multimodal_support(base_url: str, model_id: str) -> bool:
    """
    Query /upstream/{model_id}/props endpoint to check for modalities.vision support.

    Args:
        base_url: Base URL for the ik_llama.cpp endpoint
        model_id: ID of the model to check

    Returns:
        bool: True if model supports vision/multimodal, False otherwise
    """
    try:
        url = f"{base_url}/upstream/{model_id}/props"
        logger.info(f"Checking multimodal support for {model_id} at: {url}")

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Check modalities.vision field
        modalities = data.get("modalities", {})
        vision_support = modalities.get("vision", False)

        if vision_support:
            logger.info(f"Model {model_id} supports vision/multimodal")
        else:
            logger.info(f"Model {model_id} does not support vision/multimodal")

        return vision_support

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection failed to {base_url}/upstream/{model_id}/props: {e}")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"Timeout querying {base_url}/upstream/{model_id}/props")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return False
    except (KeyError, ValueError) as e:
        logger.error(f"Failed to parse response: {e}")
        return False


# Define prompt templates for different models
PROMPT_TEMPLATES = {
    "deepseek-ocr": {
        "system": None,
        "user": "Free OCR.",
        "extra_body": {
            "skip_special_tokens": False,
            "vllm_xargs": {
                "ngram_size": 30,
                "window_size": 90,
                "whitelist_token_ids": [128821, 128822],
            },
        },
    },
    "default_multimodal": {
        "system": "You are an OCR assistant. Extract all text from the image accurately.",
        "user": "Please perform OCR on this image and extract all visible text. Format the output as markdown.",
        "extra_body": None,
    },
}


def get_prompt_template(model_id: str) -> dict:
    """
    Get the appropriate prompt template for a given model ID.

    Args:
        model_id: The model identifier string

    Returns:
        dict: Prompt template with system, user, and extra_body keys
    """
    if "deepseek-ocr" in model_id.lower():
        return PROMPT_TEMPLATES["deepseek-ocr"]
    return PROMPT_TEMPLATES["default_multimodal"]


def process_pdf_pages(
    doc: fitz.Document,
    client: OpenAI,
    model_id: str,
    prompt_template: dict,
) -> list:
    """
    Process all pages in a PDF document using the specified model and prompt template.

    Args:
        doc: The PDF document object
        client: The OpenAI client instance
        model_id: The model identifier to use
        prompt_template: The prompt template with system, user, and extra_body

    Returns:
        list: List of extracted text for each page
    """
    results = []
    system_prompt = prompt_template.get("system")
    user_prompt = prompt_template["user"]
    extra_body = prompt_template.get("extra_body")

    for page_num in range(doc.page_count):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=144, colorspace=fitz.csRGB)
        img_bytes = pix.tobytes("png")
        pix = None
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        img_data_url = f"data:image/png;base64,{img_base64}"

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": img_data_url}},
                    {"type": "text", "text": user_prompt},
                ],
            }
        )

        # Build API call parameters
        api_params = {
            "model": model_id,
            "messages": messages,
            "temperature": 0.0,
        }

        if extra_body:
            api_params["extra_body"] = extra_body

        response = client.chat.completions.create(**api_params)

        if not response.choices or len(response.choices) == 0:
            raise Exception(f"No OCR response for page {page_num + 1}")

        result_text = response.choices[0].message.content
        results.append(f"--- Page {page_num + 1} ---\n{result_text}")

        img_data_url = None
        img_base64 = None

    return results


def process_with_deepseek_ocr(pdf_path: str, output_format: str) -> str:
    """
    Process PDF using DeepSeek-OCR model.

    Args:
        pdf_path: Path to the PDF file
        output_format: Output format (markdown or text)

    Returns:
        str: Extracted text from the PDF

    Raises:
        Exception: If PDF processing fails
    """
    base_url = os.getenv("DEEPSEEK_OCR_BASE_URL")
    if not base_url:
        raise Exception(
            "DEEPSEEK_OCR_BASE_URL not set. Set it via environment variable or .env file"
        )

    logger.info(f"Processing PDF with DeepSeek-OCR: {pdf_path}")

    doc = None
    try:
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            raise Exception("PDF has no pages")

        client = OpenAI(api_key="EMPTY", base_url=base_url, timeout=3600)
        prompt_template = get_prompt_template("deepseek-ocr")

        results = process_pdf_pages(doc, client, "deepseek-ocr", prompt_template)

        output = "\n\n".join(results)
        return output

    finally:
        if doc is not None:
            doc.close()


def process_with_current_model(
    pdf_path: str, output_format: str, model_id: str, base_url: str
) -> str:
    """
    Process PDF using the currently loaded multimodal model.

    Args:
        pdf_path: Path to the PDF file
        output_format: Output format (markdown or text)
        model_id: The ID of the currently loaded model
        base_url: Base URL for the API endpoint

    Returns:
        str: Extracted text from the PDF

    Raises:
        Exception: If PDF processing fails
    """
    logger.info(f"Processing PDF with current model ({model_id}): {pdf_path}")

    doc = None
    try:
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            raise Exception("PDF has no pages")

        # Use the upstream endpoint for the current model
        upstream_url = f"{base_url}/upstream/{model_id}/v1"
        client = OpenAI(api_key="EMPTY", base_url=upstream_url, timeout=3600)
        prompt_template = get_prompt_template(model_id)

        results = process_pdf_pages(doc, client, model_id, prompt_template)

        output = "\n\n".join(results)
        return output

    finally:
        if doc is not None:
            doc.close()


def route_ocr_request(pdf_path: str, output_format: str) -> str:
    """
    Route OCR request based on VRAM and model capabilities.

    Args:
        pdf_path: Path to the PDF file
        output_format: Output format (markdown or text)

    Returns:
        str: OCR result text

    Exits:
        0: Success (DeepSeek-OCR or current multimodal model used)
        1: General error (file not found, processing error, etc.)
        3: INSUFFICIENT_VRAM_NO_MULTIMODAL (not enough VRAM and current model lacks vision support)
    """
    # Get the base URL for API calls (single endpoint for all operations)
    base_url = os.getenv("DEEPSEEK_OCR_BASE_URL")

    if not base_url:
        raise Exception(
            "DEEPSEEK_OCR_BASE_URL not set. Set it via environment variable or .env file"
        )

    # Get configurable threshold (default: 17 GB)
    try:
        vram_threshold_gb = int(os.getenv("PDF_OCR_VRAM_THRESHOLD_GB", "17"))
    except ValueError:
        logger.warning("Invalid PDF_OCR_VRAM_THRESHOLD_GB value, using default 17")
        vram_threshold_gb = 17

    vram_threshold_mb = vram_threshold_gb * 1024

    # Check VRAM availability
    try:
        has_sufficient_vram, free_vram_mb = check_vram_availability()
    except Exception as e:
        logger.error(f"Failed to check VRAM availability: {e}")
        # Fall back to DeepSeek-OCR if VRAM check fails
        logger.info("VRAM check failed, falling back to DeepSeek-OCR")
        return process_with_deepseek_ocr(pdf_path, output_format)

    logger.info(
        f"VRAM Check: {free_vram_mb} MB free, threshold: {vram_threshold_mb} MB "
        f"({vram_threshold_gb} GB)"
    )

    if has_sufficient_vram and free_vram_mb >= vram_threshold_mb:
        # Use DeepSeek-OCR
        logger.info("Sufficient VRAM available, using DeepSeek-OCR")
        return process_with_deepseek_ocr(pdf_path, output_format)
    else:
        # Check if current model supports multimodal
        logger.info("Insufficient VRAM for DeepSeek-OCR, checking current model")
        current_model = get_current_model(base_url)

        if current_model and check_multimodal_support(base_url, current_model):
            # Use current multimodal model
            logger.info(f"Using current multimodal model: {current_model}")
            return process_with_current_model(
                pdf_path, output_format, current_model, base_url
            )
        else:
            # Exit with code 3
            error_msg = (
                f"INSUFFICIENT_VRAM_NO_MULTIMODAL: DeepSeek-OCR requires ~{vram_threshold_gb}GB VRAM "
                f"but only {free_vram_mb // 1024} GB available. "
                f"Current model '{current_model}' does not support multimodal/vision capabilities."
            )
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            sys.exit(3)


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
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    # Configure verbose logging if requested
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)

    pdf_path = args.pdf_path

    if not Path(pdf_path).exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    try:
        # Use the new routing system
        output = route_ocr_request(pdf_path, args.output_format)
        print(output)
    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
