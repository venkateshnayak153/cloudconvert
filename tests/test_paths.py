"""
Unit tests for helper path collision avoidance logic using unittest.
"""
from pathlib import Path
import tempfile
import unittest
from helper.utils.paths import resolve_output_path


class TestPaths(unittest.TestCase):
    def test_resolve_output_path_non_colliding(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = Path(tmp_dir) / "report.docx"
            input_file.write_text("dummy")

            dest = resolve_output_path(str(input_file), "pdf")
            expected = (Path(tmp_dir) / "report_converted.pdf").resolve()
            self.assertEqual(dest.resolve(), expected)

    def test_resolve_output_path_incrementing_collision(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = Path(tmp_dir) / "report.docx"
            input_file.write_text("dummy")

            first_dest = Path(tmp_dir) / "report_converted.pdf"
            first_dest.write_text("exists")

            dest2 = resolve_output_path(str(input_file), "pdf")
            expected2 = (Path(tmp_dir) / "report_converted_2.pdf").resolve()
            self.assertEqual(dest2.resolve(), expected2)

            dest2.write_text("exists")
            dest3 = resolve_output_path(str(input_file), "pdf")
            expected3 = (Path(tmp_dir) / "report_converted_3.pdf").resolve()
            self.assertEqual(dest3.resolve(), expected3)

    def test_resolve_output_path_custom_dir(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as out_dir:
            input_file = Path(src_dir) / "slides.pptx"
            input_file.write_text("dummy")

            dest = resolve_output_path(str(input_file), "pdf", out_dir=out_dir)
            expected = (Path(out_dir) / "slides_converted.pdf").resolve()
            self.assertEqual(dest.resolve(), expected)


if __name__ == "__main__":
    unittest.main()
