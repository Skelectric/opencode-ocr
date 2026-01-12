#!/usr/bin/env python3
import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent))
import pdf_ocr_backend


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
                    pdf_ocr_backend.main()

        mock_client.chat.completions.create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
