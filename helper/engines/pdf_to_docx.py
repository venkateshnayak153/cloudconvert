"""
PDF to DOCX engine adapter using pdf2docx.
"""
from pathlib import Path
from typing import Optional

from helper.engines.base import BaseEngine, EngineError, ProgressCallback


class PdfToDocxEngine(BaseEngine):
    name: str = "pdf2docx"

    def is_available(self) -> bool:
        try:
            import pdf2docx  # noqa: F401
            return True
        except ImportError:
            return False

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        target_ext: str,
        progress_cb: Optional[ProgressCallback] = None,
        **kwargs,
    ) -> Path:
        if not self.is_available():
            raise EngineError("NO_ENGINE", "pdf2docx library is not available.")

        if target_ext.lstrip(".").lower() != "docx":
            raise EngineError("UNSUPPORTED_TYPE", f"Engine {self.name} only converts to DOCX.")

        from pdf2docx import Converter

        if progress_cb:
            progress_cb(10, "Initializing PDF to DOCX converter...")

        try:
            cv = Converter(str(input_path))
            if progress_cb:
                progress_cb(40, "Parsing PDF layout and converting pages...")
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cv.convert(str(output_path), start=0, end=None)
            cv.close()

            if not output_path.exists():
                raise EngineError("CORRUPT_FILE", "pdf2docx did not generate the target file.")

            if progress_cb:
                progress_cb(100, "Done")

            return output_path
        except Exception as e:
            raise EngineError("ENGINE_CRASH", f"PDF to DOCX conversion failed: {e}")
