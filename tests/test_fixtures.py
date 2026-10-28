"""
Integration tests verifying detector behavior against all test fixtures.
"""
from pathlib import Path
import unittest

from helper.detector import DetectionError, detect_file

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class TestFixtures(unittest.TestCase):
    def test_sample_pdf(self):
        res = detect_file(str(FIXTURES_DIR / "sample.pdf"))
        self.assertEqual(res.format, "pdf")
        self.assertIn("docx", res.valid_targets)
        self.assertIn("pptx", res.valid_targets)

    def test_sample_docx(self):
        res = detect_file(str(FIXTURES_DIR / "sample.docx"))
        self.assertEqual(res.format, "docx")
        self.assertIn("pdf", res.valid_targets)

    def test_sample_pptx(self):
        res = detect_file(str(FIXTURES_DIR / "sample.pptx"))
        self.assertEqual(res.format, "pptx")
        self.assertIn("pdf", res.valid_targets)

    def test_encrypted_pdf(self):
        with self.assertRaises(DetectionError) as ctx:
            detect_file(str(FIXTURES_DIR / "encrypted.pdf"))
        self.assertEqual(ctx.exception.code, "PASSWORD_PROTECTED")

    def test_corrupt_pdf(self):
        with self.assertRaises(DetectionError) as ctx:
            detect_file(str(FIXTURES_DIR / "corrupt.pdf"))
        self.assertEqual(ctx.exception.code, "CORRUPT_FILE")

    def test_wrong_extension(self):
        with self.assertRaises(DetectionError) as ctx:
            detect_file(str(FIXTURES_DIR / "wrong_extension.docx"))
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_TYPE")


if __name__ == "__main__":
    unittest.main()
