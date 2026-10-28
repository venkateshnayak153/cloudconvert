"""
Conversion registry and pipeline executor.
Maps (source_format, target_format) to a sequence of conversion steps
with automatic fallback to alternative available engines.
"""
from dataclasses import dataclass
from pathlib import Path
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

from helper.engines.base import BaseEngine, EngineError, ProgressCallback
from helper.engines.libreoffice import LibreOfficeEngine
from helper.engines.office_mac import MacOfficeEngine
from helper.engines.pdf_to_docx import PdfToDocxEngine
from helper.engines.pdf_to_pptx import PdfToPptxEngine
from helper.engines.word_com import WindowsCOMEngine


@dataclass
class Step:
    target_ext: str
    engine_candidates: List[BaseEngine]


class Registry:
    def __init__(self, preferred_engine: Optional[str] = None):
        self.preferred_engine = preferred_engine
        self.libreoffice = LibreOfficeEngine()
        self.mac_office = MacOfficeEngine()
        self.win_office = WindowsCOMEngine()
        self.pdf2docx = PdfToDocxEngine()
        self.pdf_pptx = PdfToPptxEngine()

    def detect_engines(self) -> Dict[str, bool]:
        """Returns availability status for all known engines."""
        word_avail = False
        ppt_avail = False

        if sys.platform == "darwin":
            word_avail = self.mac_office.is_word_installed()
            ppt_avail = self.mac_office.is_powerpoint_installed()
        elif sys.platform == "win32":
            word_avail = self.win_office.is_available()
            ppt_avail = self.win_office.is_available()

        return {
            "word": word_avail,
            "powerpoint": ppt_avail,
            "libreoffice": self.libreoffice.is_available(),
            "pdf2docx": self.pdf2docx.is_available(),
            "pdf_to_pptx": self.pdf_pptx.is_available(),
        }

    def _get_office_engine_for(self, src: str, dst: str) -> Optional[BaseEngine]:
        if sys.platform == "darwin" and self.mac_office.is_available():
            return self.mac_office
        if sys.platform == "win32" and self.win_office.is_available():
            return self.win_office
        return None

    def _get_engine_order(self, src: str, dst: str) -> List[BaseEngine]:
        """Determines ordered engine candidates based on OS and user preference."""
        office_eng = self._get_office_engine_for(src, dst)
        lo_eng = self.libreoffice

        # If user explicitly preferred an engine
        if self.preferred_engine == "libreoffice":
            candidates = [lo_eng]
            if office_eng:
                candidates.append(office_eng)
            return candidates
        elif self.preferred_engine == "office":
            candidates = []
            if office_eng:
                candidates.append(office_eng)
            candidates.append(lo_eng)
            return candidates

        # Default per build.md:
        # On Windows: Word/PPT then LibreOffice
        # On macOS: LibreOffice preferred or Office if available
        # On Linux: LibreOffice
        if sys.platform == "win32":
            candidates = []
            if office_eng:
                candidates.append(office_eng)
            candidates.append(lo_eng)
            return candidates
        else:
            candidates = []
            if lo_eng.is_available():
                candidates.append(lo_eng)
            if office_eng:
                candidates.append(office_eng)
            if not candidates:
                # Include lo_eng as fallback so informative error is thrown
                candidates = [lo_eng]
            return candidates

    def get_pipeline(self, src: str, dst: str) -> List[Step]:
        src = src.lower().lstrip(".")
        dst = dst.lower().lstrip(".")

        if src == dst:
            raise EngineError("UNSUPPORTED_TYPE", f"Source and target format are identical ({src}).")

        # 1. DOC/DOCX to PDF
        if src in {"doc", "docx"} and dst == "pdf":
            return [Step(target_ext="pdf", engine_candidates=self._get_engine_order(src, dst))]

        # 2. PPT/PPTX to PDF
        if src in {"ppt", "pptx"} and dst == "pdf":
            return [Step(target_ext="pdf", engine_candidates=self._get_engine_order(src, dst))]

        # 3. PDF to DOCX
        if src == "pdf" and dst == "docx":
            return [Step(target_ext="docx", engine_candidates=[self.pdf2docx])]

        # 4. PDF to DOC (PDF -> DOCX via pdf2docx, then DOCX -> DOC via Office/LibreOffice)
        if src == "pdf" and dst == "doc":
            return [
                Step(target_ext="docx", engine_candidates=[self.pdf2docx]),
                Step(target_ext="doc", engine_candidates=self._get_engine_order("docx", "doc")),
            ]

        # 5. PDF to PPTX
        if src == "pdf" and dst == "pptx":
            return [Step(target_ext="pptx", engine_candidates=[self.pdf_pptx])]

        # 6. PDF to PPT (PDF -> PPTX via pdf_pptx, then PPTX -> PPT via Office/LibreOffice)
        if src == "pdf" and dst == "ppt":
            return [
                Step(target_ext="pptx", engine_candidates=[self.pdf_pptx]),
                Step(target_ext="ppt", engine_candidates=self._get_engine_order("pptx", "ppt")),
            ]

        # 7. DOC <-> DOCX
        if (src == "doc" and dst == "docx") or (src == "docx" and dst == "doc"):
            return [Step(target_ext=dst, engine_candidates=self._get_engine_order(src, dst))]

        # 8. PPT <-> PPTX
        if (src == "ppt" and dst == "pptx") or (src == "pptx" and dst == "ppt"):
            return [Step(target_ext=dst, engine_candidates=self._get_engine_order(src, dst))]

        raise EngineError("UNSUPPORTED_TYPE", f"No conversion route registered from {src} to {dst}.")

    def execute(
        self,
        input_path: Path,
        output_path: Path,
        target_ext: str,
        progress_cb: Optional[ProgressCallback] = None,
        pptx_mode: str = "image",
    ) -> Path:
        src_ext = input_path.suffix.lower().lstrip(".")
        target_ext = target_ext.lower().lstrip(".")

        pipeline = self.get_pipeline(src_ext, target_ext)
        total_steps = len(pipeline)

        current_file = input_path
        temp_files_to_cleanup: List[Path] = []

        try:
            for step_idx, step in enumerate(pipeline):
                is_last = (step_idx == total_steps - 1)
                if is_last:
                    step_out = output_path
                else:
                    # Intermediate temp file
                    tmp = tempfile.NamedTemporaryFile(suffix=f".{step.target_ext}", delete=False)
                    tmp.close()
                    step_out = Path(tmp.name)
                    temp_files_to_cleanup.append(step_out)

                def step_progress_relay(pct: int, msg: str):
                    if progress_cb:
                        step_base = int((step_idx / total_steps) * 100)
                        step_share = int(pct / total_steps)
                        overall_pct = min(99, step_base + step_share)
                        progress_cb(overall_pct, f"[Step {step_idx + 1}/{total_steps}] {msg}")

                # Try engines in order of priority until one succeeds
                last_error: Optional[EngineError] = None
                success = False

                for engine in step.engine_candidates:
                    if not engine.is_available():
                        last_error = EngineError("NO_ENGINE", f"Required engine '{engine.name}' is not installed.")
                        continue

                    try:
                        step_out = engine.convert(
                            input_path=current_file,
                            output_path=step_out,
                            target_ext=step.target_ext,
                            progress_cb=step_progress_relay,
                            pptx_mode=pptx_mode,
                        )
                        success = True
                        break
                    except EngineError as e:
                        last_error = e
                        # Fallback to next engine candidate
                        continue

                if not success:
                    if last_error:
                        raise last_error
                    raise EngineError("NO_ENGINE", "No converter engine available for this conversion.")

                current_file = step_out

            if progress_cb:
                progress_cb(100, "Done")

            return output_path

        finally:
            for tmp in temp_files_to_cleanup:
                try:
                    if tmp.exists():
                        tmp.unlink()
                except Exception:
                    pass
