#!/usr/bin/env python3
import sys
import os
import json
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

    # Validate DEEPSEEK_OCR_BASE_URL (required)
    deepseek_url = os.getenv("DEEPSEEK_OCR_BASE_URL")
    if deepseek_url and not deepseek_url.startswith(("http://", "https://")):
        errors.append(
            f"DEEPSEEK_OCR_BASE_URL must be a valid URL starting with http:// or https://: {deepseek_url}"
        )

    # Check for routing config file (warning only if missing)
    tool_dir = Path(__file__).parent
    config_path = tool_dir / "ocr_routing.json"
    if not config_path.exists():
        warnings.append(f"Routing config not found at {config_path}, using defaults")

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

        # DeepSeek-OCR needs the /v1 endpoint
        deepseek_url = base_url.rstrip("/") + "/v1"
        client = OpenAI(api_key="EMPTY", base_url=deepseek_url, timeout=3600)
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


def load_ocr_routing_config(config_path: Optional[Path] = None) -> dict:
    """
    Load OCR routing configuration from JSON file.

    Args:
        config_path: Path to the routing config file. If None, uses default location.

    Returns:
        dict: Routing configuration with model mappings
    """
    if config_path is None:
        tool_dir = Path(__file__).parent
        config_path = tool_dir / "ocr_routing.json"

    default_config = {"ocr_routing": {}, "default": "current_model"}

    if not config_path.exists():
        logger.warning(f"Routing config not found at {config_path}, using defaults")
        return default_config

    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        # Validate config structure
        if "ocr_routing" not in config:
            config["ocr_routing"] = {}
        if "default" not in config:
            config["default"] = "current_model"

        return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in routing config: {e}")
        return default_config
    except Exception as e:
        logger.error(f"Error loading routing config: {e}")
        return default_config


def get_ocr_method_for_model(model_id: str, config: dict) -> str:
    """
    Determine OCR method for a given model based on routing configuration.

    Args:
        model_id: The current model ID
        config: The routing configuration dictionary

    Returns:
        str: "deepseek-ocr" or "current_model"
    """
    routing = config.get("ocr_routing", {})
    default = config.get("default", "current_model")

    # Check for exact match
    if model_id in routing:
        return routing[model_id]

    # Check for partial match (e.g., "kimi-k2.5" matches "ik_llama.cpp/kimi-k2.5-experimental")
    for pattern, method in routing.items():
        if pattern in model_id or model_id in pattern:
            return method

    # Return default
    return default


def route_ocr_request(pdf_path: str, output_format: str) -> str:
    """
    Route OCR request based on model-based configuration.

    Args:
        pdf_path: Path to the PDF file
        output_format: Output format (markdown or text)

    Returns:
        str: OCR result text

    Exits:
        0: Success (DeepSeek-OCR or current multimodal model used)
        1: General error (file not found, processing error, DeepSeek-OCR failure, etc.)
        3: NO_OCR_SUPPORT (current_model routing but model lacks vision support)
    """
    base_url = os.getenv("DEEPSEEK_OCR_BASE_URL")
    if not base_url:
        raise Exception("DEEPSEEK_OCR_BASE_URL not set")

    # Load routing configuration
    routing_config = load_ocr_routing_config()

    # Get current model
    current_model = get_current_model(base_url)
    if not current_model:
        raise Exception("No model currently loaded")

    # Determine OCR method based on configuration
    ocr_method = get_ocr_method_for_model(current_model, routing_config)

    logger.info(f"Model: {current_model}, OCR method: {ocr_method}")

    if ocr_method == "deepseek-ocr":
        # Use DeepSeek-OCR
        logger.info(f"Routing to DeepSeek-OCR based on config for {current_model}")
        try:
            return process_with_deepseek_ocr(pdf_path, output_format)
        except Exception as e:
            # DeepSeek-OCR failed - this is a general error (Exit 1)
            logger.error(f"DeepSeek-OCR failed: {e}")
            raise
    else:
        # Use current model - check if it supports vision
        logger.info(f"Routing to current model based on config for {current_model}")

        if check_multimodal_support(base_url, current_model):
            return process_with_current_model(
                pdf_path, output_format, current_model, base_url
            )
        else:
            # Current model doesn't support vision - Exit 3
            error_msg = (
                f"NO_OCR_SUPPORT: Model '{current_model}' is configured to use "
                f"current_model for OCR but does not support multimodal/vision capabilities. "
                f"Add '{current_model}' to ocr_routing.json with 'deepseek-ocr' value "
                f"to use DeepSeek-OCR instead."
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
