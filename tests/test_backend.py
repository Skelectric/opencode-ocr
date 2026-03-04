#!/usr/bin/env python3
import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "pdf-ocr" / "tool"))
import pdf_ocr_backend


class TestOCRRoutingConfig(unittest.TestCase):
    """Unit tests for OCR routing configuration functionality."""

    def test_load_ocr_routing_config_existing_valid(self):
        """Test loading existing valid config file."""
        config_content = json.dumps(
            {"ocr_routing": {"test-model": "deepseek-ocr"}, "default": "current_model"}
        )

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch.object(Path, "exists", return_value=True):
                result = pdf_ocr_backend.load_ocr_routing_config(Path("/fake/path"))

        self.assertEqual(result["ocr_routing"]["test-model"], "deepseek-ocr")
        self.assertEqual(result["default"], "current_model")

    def test_load_ocr_routing_config_nonexistent(self):
        """Test loading non-existent config file returns defaults."""
        with patch.object(Path, "exists", return_value=False):
            result = pdf_ocr_backend.load_ocr_routing_config(Path("/fake/path"))

        self.assertEqual(result["ocr_routing"], {})
        self.assertEqual(result["default"], "current_model")

    def test_load_ocr_routing_config_invalid_json(self):
        """Test loading invalid JSON returns defaults."""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            with patch.object(Path, "exists", return_value=True):
                result = pdf_ocr_backend.load_ocr_routing_config(Path("/fake/path"))

        self.assertEqual(result["ocr_routing"], {})
        self.assertEqual(result["default"], "current_model")

    def test_load_ocr_routing_config_missing_ocr_routing_key(self):
        """Test config with missing ocr_routing key gets default."""
        config_content = json.dumps({"default": "deepseek-ocr"})

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch.object(Path, "exists", return_value=True):
                result = pdf_ocr_backend.load_ocr_routing_config(Path("/fake/path"))

        self.assertEqual(result["ocr_routing"], {})
        self.assertEqual(result["default"], "deepseek-ocr")

    def test_load_ocr_routing_config_missing_default_key(self):
        """Test config with missing default key gets default."""
        config_content = json.dumps({"ocr_routing": {"model": "deepseek-ocr"}})

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch.object(Path, "exists", return_value=True):
                result = pdf_ocr_backend.load_ocr_routing_config(Path("/fake/path"))

        self.assertEqual(result["default"], "current_model")

    def test_get_ocr_method_for_model_exact_match(self):
        """Test exact model match in routing config."""
        config = {
            "ocr_routing": {"ik_llama.cpp/kimi-k2.5": "deepseek-ocr"},
            "default": "current_model",
        }

        result = pdf_ocr_backend.get_ocr_method_for_model(
            "ik_llama.cpp/kimi-k2.5", config
        )
        self.assertEqual(result, "deepseek-ocr")

    def test_get_ocr_method_for_model_partial_match_pattern_in_model(self):
        """Test partial match where pattern is contained in model_id."""
        config = {
            "ocr_routing": {"kimi-k2.5": "deepseek-ocr"},
            "default": "current_model",
        }

        result = pdf_ocr_backend.get_ocr_method_for_model(
            "ik_llama.cpp/kimi-k2.5-experimental", config
        )
        self.assertEqual(result, "deepseek-ocr")

    def test_get_ocr_method_for_model_partial_match_model_in_pattern(self):
        """Test partial match where model_id is contained in pattern."""
        config = {
            "ocr_routing": {"ik_llama.cpp/kimi-k2.5-experimental": "deepseek-ocr"},
            "default": "current_model",
        }

        result = pdf_ocr_backend.get_ocr_method_for_model("kimi-k2.5", config)
        self.assertEqual(result, "deepseek-ocr")

    def test_get_ocr_method_for_model_no_match_returns_default(self):
        """Test no match returns default method."""
        config = {
            "ocr_routing": {"other-model": "deepseek-ocr"},
            "default": "current_model",
        }

        result = pdf_ocr_backend.get_ocr_method_for_model("unknown-model", config)
        self.assertEqual(result, "current_model")

    def test_get_ocr_method_for_model_empty_config(self):
        """Test empty config returns default method."""
        config = {"ocr_routing": {}, "default": "current_model"}

        result = pdf_ocr_backend.get_ocr_method_for_model("any-model", config)
        self.assertEqual(result, "current_model")


class TestModelDetection(unittest.TestCase):
    """Unit tests for model detection functionality."""

    @patch("pdf_ocr_backend.requests.get")
    def test_get_current_model_list_format(self, mock_get):
        """Test get_current_model with list response format."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"model": "test-model-v1", "id": "model-123"}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = pdf_ocr_backend.get_current_model("http://test:8080")

        self.assertEqual(result, "test-model-v1")
        mock_get.assert_called_once_with("http://test:8080/running", timeout=10)

    @patch("pdf_ocr_backend.requests.get")
    def test_get_current_model_dict_format(self, mock_get):
        """Test get_current_model with dict response format."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "model": "test-model-v2",
            "status": "running",
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = pdf_ocr_backend.get_current_model("http://test:8080")

        self.assertEqual(result, "test-model-v2")

    @patch("pdf_ocr_backend.requests.get")
    def test_get_current_model_empty_list(self, mock_get):
        """Test get_current_model with empty list response."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = pdf_ocr_backend.get_current_model("http://test:8080")

        self.assertIsNone(result)

    @patch("pdf_ocr_backend.requests.get")
    def test_get_current_model_connection_error(self, mock_get):
        """Test get_current_model with connection failure."""
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        result = pdf_ocr_backend.get_current_model("http://test:8080")

        self.assertIsNone(result)

    @patch("pdf_ocr_backend.requests.get")
    def test_get_current_model_timeout(self, mock_get):
        """Test get_current_model with timeout."""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        result = pdf_ocr_backend.get_current_model("http://test:8080")

        self.assertIsNone(result)

    @patch("pdf_ocr_backend.requests.get")
    def test_check_multimodal_support_vision_true(self, mock_get):
        """Test check_multimodal_support with vision=true."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "modalities": {"vision": True, "audio": False}
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = pdf_ocr_backend.check_multimodal_support(
            "http://test:8080", "test-model"
        )

        self.assertTrue(result)
        mock_get.assert_called_once_with(
            "http://test:8080/upstream/test-model/props", timeout=10
        )

    @patch("pdf_ocr_backend.requests.get")
    def test_check_multimodal_support_vision_false(self, mock_get):
        """Test check_multimodal_support with vision=false."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "modalities": {"vision": False, "audio": True}
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = pdf_ocr_backend.check_multimodal_support(
            "http://test:8080", "test-model"
        )

        self.assertFalse(result)

    @patch("pdf_ocr_backend.requests.get")
    def test_check_multimodal_support_missing_modalities(self, mock_get):
        """Test check_multimodal_support with missing modalities field."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "test-model", "name": "Test Model"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = pdf_ocr_backend.check_multimodal_support(
            "http://test:8080", "test-model"
        )

        self.assertFalse(result)

    @patch("pdf_ocr_backend.requests.get")
    def test_check_multimodal_support_connection_error(self, mock_get):
        """Test check_multimodal_support with connection failure."""
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        result = pdf_ocr_backend.check_multimodal_support(
            "http://test:8080", "test-model"
        )

        self.assertFalse(result)


class TestModelRouter(unittest.TestCase):
    """Unit tests for model routing functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf = os.path.join(self.temp_dir, "test.pdf")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_get_prompt_template_deepseek_ocr(self):
        """Test get_prompt_template returns deepseek-ocr template."""
        template = pdf_ocr_backend.get_prompt_template("deepseek-ocr-v1")
        self.assertIsNone(template["system"])
        self.assertEqual(template["user"], "Free OCR.")
        self.assertIsNotNone(template["extra_body"])
        self.assertIn("skip_special_tokens", template["extra_body"])

    def test_get_prompt_template_default_multimodal(self):
        """Test get_prompt_template returns default_multimodal template."""
        template = pdf_ocr_backend.get_prompt_template("qwen-vl")
        self.assertIsNotNone(template["system"])
        self.assertIn("OCR assistant", template["system"])
        self.assertEqual(template["extra_body"], None)

    @patch("pdf_ocr_backend.process_with_deepseek_ocr")
    @patch("pdf_ocr_backend.load_ocr_routing_config")
    @patch("pdf_ocr_backend.get_current_model")
    @patch.dict(os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"})
    def test_route_ocr_request_deepseek_ocr_configured_success(
        self, mock_get_model, mock_load_config, mock_process
    ):
        """Test routing to DeepSeek-OCR when configured and successful."""
        mock_get_model.return_value = "test-model"
        mock_load_config.return_value = {
            "ocr_routing": {"test-model": "deepseek-ocr"},
            "default": "current_model",
        }
        mock_process.return_value = "DeepSeek OCR result"

        result = pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(result, "DeepSeek OCR result")
        mock_process.assert_called_once_with(self.test_pdf, "markdown")

    @patch("pdf_ocr_backend.process_with_deepseek_ocr")
    @patch("pdf_ocr_backend.load_ocr_routing_config")
    @patch("pdf_ocr_backend.get_current_model")
    @patch.dict(os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"})
    def test_route_ocr_request_deepseek_ocr_configured_failure(
        self, mock_get_model, mock_load_config, mock_process
    ):
        """Test routing to DeepSeek-OCR when configured but fails (Exit 1)."""
        mock_get_model.return_value = "test-model"
        mock_load_config.return_value = {
            "ocr_routing": {"test-model": "deepseek-ocr"},
            "default": "current_model",
        }
        mock_process.side_effect = Exception("DeepSeek-OCR failed")

        with self.assertRaises(Exception) as cm:
            pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertIn("DeepSeek-OCR failed", str(cm.exception))

    @patch("pdf_ocr_backend.process_with_current_model")
    @patch("pdf_ocr_backend.check_multimodal_support")
    @patch("pdf_ocr_backend.load_ocr_routing_config")
    @patch("pdf_ocr_backend.get_current_model")
    @patch.dict(os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"})
    def test_route_ocr_request_current_model_with_vision(
        self, mock_get_model, mock_load_config, mock_multimodal, mock_process
    ):
        """Test routing to current model with vision support (Exit 0)."""
        mock_get_model.return_value = "qwen-vl"
        mock_load_config.return_value = {
            "ocr_routing": {"qwen-vl": "current_model"},
            "default": "current_model",
        }
        mock_multimodal.return_value = True
        mock_process.return_value = "Current model OCR result"

        result = pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(result, "Current model OCR result")
        mock_process.assert_called_once_with(
            self.test_pdf, "markdown", "qwen-vl", "http://test:8080/v1"
        )

    @patch("pdf_ocr_backend.check_multimodal_support")
    @patch("pdf_ocr_backend.load_ocr_routing_config")
    @patch("pdf_ocr_backend.get_current_model")
    @patch.dict(os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"})
    def test_route_ocr_request_current_model_no_vision_exit_3(
        self, mock_get_model, mock_load_config, mock_multimodal
    ):
        """Test routing to current model without vision support (Exit 3)."""
        mock_get_model.return_value = "text-only-model"
        mock_load_config.return_value = {
            "ocr_routing": {"text-only-model": "current_model"},
            "default": "current_model",
        }
        mock_multimodal.return_value = False

        with self.assertRaises(SystemExit) as cm:
            pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(cm.exception.code, 3)

    @patch("pdf_ocr_backend.process_with_current_model")
    @patch("pdf_ocr_backend.check_multimodal_support")
    @patch("pdf_ocr_backend.load_ocr_routing_config")
    @patch("pdf_ocr_backend.get_current_model")
    @patch.dict(os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"})
    def test_route_ocr_request_model_not_in_config_with_vision(
        self, mock_get_model, mock_load_config, mock_multimodal, mock_process
    ):
        """Test routing when model not in config but has vision support."""
        mock_get_model.return_value = "new-model"
        mock_load_config.return_value = {"ocr_routing": {}, "default": "current_model"}
        mock_multimodal.return_value = True
        mock_process.return_value = "OCR result"

        result = pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(result, "OCR result")

    @patch("pdf_ocr_backend.check_multimodal_support")
    @patch("pdf_ocr_backend.load_ocr_routing_config")
    @patch("pdf_ocr_backend.get_current_model")
    @patch.dict(os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"})
    def test_route_ocr_request_model_not_in_config_no_vision_exit_3(
        self, mock_get_model, mock_load_config, mock_multimodal
    ):
        """Test routing when model not in config and no vision support (Exit 3)."""
        mock_get_model.return_value = "text-model"
        mock_load_config.return_value = {"ocr_routing": {}, "default": "current_model"}
        mock_multimodal.return_value = False

        with self.assertRaises(SystemExit) as cm:
            pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(cm.exception.code, 3)

    @patch.dict(os.environ, {}, clear=True)
    def test_route_ocr_request_no_base_url(self):
        """Test route_ocr_request when DEEPSEEK_OCR_BASE_URL not set."""
        with self.assertRaises(Exception) as cm:
            pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertIn("DEEPSEEK_OCR_BASE_URL not set", str(cm.exception))

    @patch("pdf_ocr_backend.get_current_model")
    @patch.dict(os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"})
    def test_route_ocr_request_no_model_loaded(self, mock_get_model):
        """Test route_ocr_request when no model is loaded."""
        mock_get_model.return_value = None

        with self.assertRaises(Exception) as cm:
            pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertIn("No model currently loaded", str(cm.exception))


class TestPDFOCRBackend(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf = os.path.join(self.temp_dir, "test.pdf")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("pdf_ocr_backend.process_with_deepseek_ocr")
    @patch("pdf_ocr_backend.load_ocr_routing_config")
    @patch("pdf_ocr_backend.get_current_model")
    @patch("pdf_ocr_backend.fitz.open")
    @patch("pdf_ocr_backend.OpenAI")
    def test_main_with_valid_pdf(
        self,
        mock_openai,
        mock_fitz_open,
        mock_get_model,
        mock_load_config,
        mock_process,
    ):
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake_png_bytes"
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz_open.return_value = mock_doc

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Extracted text"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        mock_get_model.return_value = "test-model"
        mock_load_config.return_value = {
            "ocr_routing": {"test-model": "deepseek-ocr"},
            "default": "current_model",
        }
        mock_process.return_value = "Extracted text"

        with patch("sys.argv", ["pdf_ocr_backend.py", self.test_pdf, "markdown"]):
            with patch("builtins.print") as mock_print:
                with patch.object(Path, "exists", return_value=True):
                    with patch.dict(
                        os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"}
                    ):
                        pdf_ocr_backend.main()

        calls = mock_print.call_args_list
        self.assertTrue(any("Extracted text" in str(call) for call in calls))

    @patch("builtins.print")
    def test_main_with_nonexistent_pdf(self, mock_print):
        with patch(
            "sys.argv", ["pdf_ocr_backend.py", "/nonexistent/file.pdf", "markdown"]
        ):
            with self.assertRaises(SystemExit) as cm:
                pdf_ocr_backend.main()
            self.assertEqual(cm.exception.code, 1)

    @patch("builtins.print")
    @patch("pdf_ocr_backend.fitz.open")
    def test_main_with_corrupt_pdf(self, mock_fitz_open, mock_print):
        mock_fitz_open.side_effect = Exception("Corrupt PDF")

        with patch("sys.argv", ["pdf_ocr_backend.py", self.test_pdf, "markdown"]):
            with patch.object(Path, "exists", return_value=True):
                with self.assertRaises(SystemExit) as cm:
                    pdf_ocr_backend.main()
                self.assertEqual(cm.exception.code, 1)

    @patch("pdf_ocr_backend.fitz.open")
    @patch("pdf_ocr_backend.OpenAI")
    def test_main_with_ocr_error(self, mock_openai, mock_fitz_open):
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake_png_bytes"
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz_open.return_value = mock_doc

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception(
            "OCR service unavailable"
        )
        mock_openai.return_value = mock_client

        with patch("sys.argv", ["pdf_ocr_backend.py", self.test_pdf, "markdown"]):
            with patch.object(Path, "exists", return_value=True):
                with patch.dict(
                    os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"}
                ):
                    with self.assertRaises(SystemExit) as cm:
                        pdf_ocr_backend.main()
                    self.assertEqual(cm.exception.code, 1)

    @patch("pdf_ocr_backend.process_with_deepseek_ocr")
    @patch("pdf_ocr_backend.load_ocr_routing_config")
    @patch("pdf_ocr_backend.get_current_model")
    @patch("pdf_ocr_backend.fitz.open")
    @patch("pdf_ocr_backend.OpenAI")
    def test_main_default_output_format(
        self,
        mock_openai,
        mock_fitz_open,
        mock_get_model,
        mock_load_config,
        mock_process,
    ):
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake_png_bytes"
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz_open.return_value = mock_doc

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Default format text"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        mock_get_model.return_value = "test-model"
        mock_load_config.return_value = {
            "ocr_routing": {"test-model": "deepseek-ocr"},
            "default": "current_model",
        }
        mock_process.return_value = "Default format text"

        with patch("sys.argv", ["pdf_ocr_backend.py", self.test_pdf]):
            with patch("builtins.print"):
                with patch.object(Path, "exists", return_value=True):
                    with patch.dict(
                        os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"}
                    ):
                        pdf_ocr_backend.main()

        mock_process.assert_called_once()

    @patch("builtins.print")
    @patch("pdf_ocr_backend.fitz.open")
    def test_main_without_base_url(self, mock_fitz_open, mock_print):
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_fitz_open.return_value = mock_doc

        with patch("sys.argv", ["pdf_ocr_backend.py", self.test_pdf, "markdown"]):
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(Path, "exists", return_value=True):
                    with self.assertRaises(SystemExit) as cm:
                        pdf_ocr_backend.main()
                    self.assertEqual(cm.exception.code, 1)

        calls = mock_print.call_args_list
        self.assertTrue(
            any("DEEPSEEK_OCR_BASE_URL not set" in str(call) for call in calls)
        )


class TestExitCode3(unittest.TestCase):
    """Unit tests for Exit 3 (NO_OCR_SUPPORT) scenarios."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf = os.path.join(self.temp_dir, "test.pdf")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("pdf_ocr_backend.check_multimodal_support")
    @patch("pdf_ocr_backend.load_ocr_routing_config")
    @patch("pdf_ocr_backend.get_current_model")
    @patch.dict(os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"})
    def test_exit_3_only_when_current_model_configured_no_vision(
        self, mock_get_model, mock_load_config, mock_multimodal
    ):
        """Verify Exit 3 only occurs when current_model configured but no vision support."""
        mock_get_model.return_value = "text-model"
        mock_load_config.return_value = {
            "ocr_routing": {"text-model": "current_model"},
            "default": "current_model",
        }
        mock_multimodal.return_value = False

        with self.assertRaises(SystemExit) as cm:
            pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(cm.exception.code, 3)

    @patch("pdf_ocr_backend.check_multimodal_support")
    @patch("pdf_ocr_backend.load_ocr_routing_config")
    @patch("pdf_ocr_backend.get_current_model")
    @patch.dict(os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"})
    def test_exit_3_error_message_format(
        self, mock_get_model, mock_load_config, mock_multimodal
    ):
        """Verify error message includes model name and configuration instructions."""
        mock_get_model.return_value = "my-text-model"
        mock_load_config.return_value = {
            "ocr_routing": {"my-text-model": "current_model"},
            "default": "current_model",
        }
        mock_multimodal.return_value = False

        with patch("sys.stderr") as mock_stderr:
            with self.assertRaises(SystemExit):
                pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

            # Check that error message was printed to stderr
            mock_stderr.write.assert_called()
            error_output = ""
            for call in mock_stderr.write.call_args_list:
                args = call[0]
                if args:
                    error_output += str(args[0])

            self.assertIn("NO_OCR_SUPPORT", error_output)
            self.assertIn("my-text-model", error_output)
            self.assertIn("ocr_routing.json", error_output)
            self.assertIn("deepseek-ocr", error_output)


if __name__ == "__main__":
    unittest.main()
