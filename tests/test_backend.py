#!/usr/bin/env python3
import unittest
import tempfile
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "pdf-ocr" / "tool"))
import pdf_ocr_backend


class TestVRAMDetection(unittest.TestCase):
    """Unit tests for VRAM detection functionality."""

    @patch("pdf_ocr_backend.subprocess.run")
    def test_check_vram_single_gpu(self, mock_subprocess):
        """Test VRAM detection with a single GPU."""
        mock_result = MagicMock()
        mock_result.stdout = "16384\n"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        has_sufficient, free_mb = pdf_ocr_backend.check_vram_availability()

        self.assertTrue(has_sufficient)
        self.assertEqual(free_mb, 16384)
        mock_subprocess.assert_called_once()

    @patch("pdf_ocr_backend.subprocess.run")
    def test_check_vram_multiple_gpus(self, mock_subprocess):
        """Test VRAM detection with multiple GPUs."""
        mock_result = MagicMock()
        mock_result.stdout = "8192\n8192\n"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        has_sufficient, free_mb = pdf_ocr_backend.check_vram_availability()

        self.assertTrue(has_sufficient)
        self.assertEqual(free_mb, 16384)

    @patch("pdf_ocr_backend.subprocess.run")
    def test_check_vram_zero_memory(self, mock_subprocess):
        """Test VRAM detection with zero free memory."""
        mock_result = MagicMock()
        mock_result.stdout = "0\n"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        has_sufficient, free_mb = pdf_ocr_backend.check_vram_availability()

        self.assertFalse(has_sufficient)
        self.assertEqual(free_mb, 0)

    @patch("pdf_ocr_backend.subprocess.run")
    def test_check_vram_command_failure(self, mock_subprocess):
        """Test VRAM detection when nvidia-smi fails."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="nvidia-smi", stderr="Command failed"
        )

        with self.assertRaises(subprocess.CalledProcessError):
            pdf_ocr_backend.check_vram_availability()

    @patch("pdf_ocr_backend.subprocess.run")
    def test_check_vram_not_found(self, mock_subprocess):
        """Test VRAM detection when nvidia-smi is not found."""
        mock_subprocess.side_effect = FileNotFoundError("nvidia-smi not found")

        with self.assertRaises(FileNotFoundError):
            pdf_ocr_backend.check_vram_availability()

    @patch("pdf_ocr_backend.subprocess.run")
    def test_check_vram_empty_output(self, mock_subprocess):
        """Test VRAM detection with empty output."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        has_sufficient, free_mb = pdf_ocr_backend.check_vram_availability()

        self.assertFalse(has_sufficient)
        self.assertEqual(free_mb, 0)

    @patch("pdf_ocr_backend.subprocess.run")
    def test_check_vram_malformed_output(self, mock_subprocess):
        """Test VRAM detection with malformed output."""
        mock_result = MagicMock()
        mock_result.stdout = "invalid\n8192\n"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        has_sufficient, free_mb = pdf_ocr_backend.check_vram_availability()

        self.assertTrue(has_sufficient)
        self.assertEqual(free_mb, 8192)


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
    @patch.dict(os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"})
    def test_route_ocr_request_no_vram_check(self, mock_process):
        """Test route_ocr_request works when only DEEPSEEK_OCR_BASE_URL is set."""
        mock_process.return_value = "OCR result"

        result = pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(result, "OCR result")
        mock_process.assert_called_once_with(self.test_pdf, "markdown")

    @patch("pdf_ocr_backend.process_with_deepseek_ocr")
    @patch("pdf_ocr_backend.check_vram_availability")
    @patch.dict(
        os.environ,
        {
            "DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1",
            "PDF_OCR_VRAM_THRESHOLD_GB": "17",
        },
    )
    def test_route_ocr_request_sufficient_vram(self, mock_vram, mock_process):
        """Test route_ocr_request uses DeepSeek-OCR when VRAM is sufficient."""
        mock_vram.return_value = (True, 20480)  # 20 GB free
        mock_process.return_value = "DeepSeek OCR result"

        result = pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(result, "DeepSeek OCR result")
        mock_process.assert_called_once_with(self.test_pdf, "markdown")

    @patch("pdf_ocr_backend.process_with_current_model")
    @patch("pdf_ocr_backend.check_multimodal_support")
    @patch("pdf_ocr_backend.get_current_model")
    @patch("pdf_ocr_backend.check_vram_availability")
    @patch.dict(
        os.environ,
        {
            "DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1",
            "PDF_OCR_VRAM_THRESHOLD_GB": "17",
        },
    )
    def test_route_ocr_request_insufficient_vram_multimodal_available(
        self, mock_vram, mock_get_model, mock_multimodal, mock_process
    ):
        """Test route_ocr_request uses current model when VRAM insufficient but model supports vision."""
        mock_vram.return_value = (True, 8192)  # 8 GB free (< 17 GB threshold)
        mock_get_model.return_value = "qwen-vl"
        mock_multimodal.return_value = True
        mock_process.return_value = "Current model OCR result"

        result = pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(result, "Current model OCR result")
        mock_process.assert_called_once_with(
            self.test_pdf, "markdown", "qwen-vl", "http://test:8080/v1"
        )

    @patch("pdf_ocr_backend.check_multimodal_support")
    @patch("pdf_ocr_backend.get_current_model")
    @patch("pdf_ocr_backend.check_vram_availability")
    @patch.dict(
        os.environ,
        {
            "DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1",
            "PDF_OCR_VRAM_THRESHOLD_GB": "17",
        },
    )
    def test_route_ocr_request_insufficient_vram_no_multimodal(
        self, mock_vram, mock_get_model, mock_multimodal
    ):
        """Test route_ocr_request exits with code 3 when VRAM insufficient and no multimodal support."""
        mock_vram.return_value = (True, 8192)  # 8 GB free
        mock_get_model.return_value = "text-only-model"
        mock_multimodal.return_value = False

        with self.assertRaises(SystemExit) as cm:
            pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(cm.exception.code, 3)

    @patch("pdf_ocr_backend.process_with_deepseek_ocr")
    @patch("pdf_ocr_backend.check_vram_availability")
    @patch.dict(
        os.environ,
        {
            "DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1",
        },
    )
    def test_route_ocr_request_default_threshold(self, mock_vram, mock_process):
        """Test route_ocr_request uses default threshold of 17 GB."""
        mock_vram.return_value = (True, 18432)  # 18 GB free (> 17 GB default)
        mock_process.return_value = "OCR result"

        result = pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(result, "OCR result")
        mock_process.assert_called_once_with(self.test_pdf, "markdown")

    @patch("pdf_ocr_backend.process_with_deepseek_ocr")
    @patch("pdf_ocr_backend.check_vram_availability")
    @patch.dict(
        os.environ,
        {
            "DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1",
            "PDF_OCR_VRAM_THRESHOLD_GB": "invalid",
        },
    )
    def test_route_ocr_request_invalid_threshold(self, mock_vram, mock_process):
        """Test route_ocr_request handles invalid threshold value gracefully."""
        mock_vram.return_value = (True, 18432)  # 18 GB free
        mock_process.return_value = "OCR result"

        result = pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(result, "OCR result")
        mock_process.assert_called_once_with(self.test_pdf, "markdown")

    @patch("pdf_ocr_backend.process_with_deepseek_ocr")
    @patch("pdf_ocr_backend.check_vram_availability")
    @patch.dict(
        os.environ,
        {
            "DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1",
        },
    )
    def test_route_ocr_request_vram_check_failure(self, mock_vram, mock_process):
        """Test route_ocr_request falls back to DeepSeek-OCR when VRAM check fails."""
        mock_vram.side_effect = Exception("nvidia-smi not found")
        mock_process.return_value = "OCR result"

        result = pdf_ocr_backend.route_ocr_request(self.test_pdf, "markdown")

        self.assertEqual(result, "OCR result")
        mock_process.assert_called_once_with(self.test_pdf, "markdown")


class TestPDFOCRBackend(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf = os.path.join(self.temp_dir, "test.pdf")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("pdf_ocr_backend.fitz.open")
    @patch("pdf_ocr_backend.OpenAI")
    def test_main_with_valid_pdf(self, mock_openai, mock_fitz_open):
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

    @patch("pdf_ocr_backend.fitz.open")
    @patch("pdf_ocr_backend.OpenAI")
    def test_main_default_output_format(self, mock_openai, mock_fitz_open):
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

        with patch("sys.argv", ["pdf_ocr_backend.py", self.test_pdf]):
            with patch("builtins.print"):
                with patch.object(Path, "exists", return_value=True):
                    with patch.dict(
                        os.environ, {"DEEPSEEK_OCR_BASE_URL": "http://test:8080/v1"}
                    ):
                        pdf_ocr_backend.main()

        mock_client.chat.completions.create.assert_called_once()

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


if __name__ == "__main__":
    unittest.main()
