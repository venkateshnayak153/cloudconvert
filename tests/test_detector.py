"""
Unit tests for file format and signature detector using standard library unittest.
"""
from pathlib import Path
import tempfile
import unittest
import zipfile

from helper.detector import DetectionError, detect_file


class TestDetector(unittest.TestCase):
    def test_missing_file(self):
        with self.assertRaises(DetectionError) as ctx:
            detect_file("/nonexistent/file.pdf")
        self.assertEqual(ctx.exception.code, "CORRUPT_FILE")

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            with self.assertRaises(DetectionError) as ctx:
                detect_file(tmp.name)
            self.assertEqual(ctx.exception.code, "CORRUPT_FILE")

    def test_unsupported_extension(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
            tmp.write(b"Hello world")
            tmp.flush()
            with self.assertRaises(DetectionError) as ctx:
                detect_file(tmp.name)
            self.assertEqual(ctx.exception.code, "UNSUPPORTED_TYPE")

    def test_valid_pdf_detection(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")
            tmp.flush()
            p = Path(tmp.name)
        try:
            res = detect_file(str(p))
            self.assertEqual(res.format, "pdf")
            self.assertIn("docx", res.valid_targets)
            self.assertIn("pptx", res.valid_targets)
        finally:
            p.unlink()

    def test_encrypted_pdf_detection(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4\n1 0 obj\n<< /Encrypt 2 0 R >>\nendobj\ntrailer\n<<>>\n%%EOF")
            tmp.flush()
            p = Path(tmp.name)
        try:
            with self.assertRaises(DetectionError) as ctx:
                detect_file(str(p))
            self.assertEqual(ctx.exception.code, "PASSWORD_PROTECTED")
        finally:
            p.unlink()

    def test_docx_detection(self):
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            p = Path(tmp.name)
        try:
            with zipfile.ZipFile(p, "w") as zf:
                zf.writestr("[Content_Types].xml", '<Types><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
                zf.writestr("word/document.xml", "<w:document></w:document>")

            res = detect_file(str(p))
            self.assertEqual(res.format, "docx")
            self.assertIn("pdf", res.valid_targets)
        finally:
            p.unlink()

    def test_signature_mismatch(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            p = Path(tmp.name)
        try:
            with zipfile.ZipFile(p, "w") as zf:
                zf.writestr("word/document.xml", "<w:document></w:document>")

            with self.assertRaises(DetectionError) as ctx:
                detect_file(str(p))
            self.assertEqual(ctx.exception.code, "UNSUPPORTED_TYPE")
        finally:
            p.unlink()


if __name__ == "__main__":
    unittest.main()
