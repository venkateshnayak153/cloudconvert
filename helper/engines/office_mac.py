"""
macOS Microsoft Office engine adapter using AppleScript via osascript.
"""
from pathlib import Path
import subprocess
import sys
from typing import Optional

from helper.engines.base import BaseEngine, EngineError, ProgressCallback


class MacOfficeEngine(BaseEngine):
    name: str = "office_mac"

    def is_word_installed(self) -> bool:
        return sys.platform == "darwin" and Path("/Applications/Microsoft Word.app").exists()

    def is_powerpoint_installed(self) -> bool:
        return sys.platform == "darwin" and Path("/Applications/Microsoft PowerPoint.app").exists()

    def is_available(self) -> bool:
        return self.is_word_installed() or self.is_powerpoint_installed()

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        target_ext: str,
        progress_cb: Optional[ProgressCallback] = None,
        timeout_seconds: int = 300,
        **kwargs,
    ) -> Path:
        if sys.platform != "darwin":
            raise EngineError("NO_ENGINE", "macOS Office engine only runs on macOS.")

        src_ext = input_path.suffix.lower().lstrip(".")
        target_ext = target_ext.lstrip(".").lower()

        is_word = src_ext in {"doc", "docx"} or (src_ext == "pdf" and target_ext in {"doc", "docx"})
        is_ppt = src_ext in {"ppt", "pptx"} or (src_ext == "pdf" and target_ext in {"ppt", "pptx"})

        if is_word and not self.is_word_installed():
            raise EngineError("NO_ENGINE", "Microsoft Word is not installed on this Mac.")
        if is_ppt and not self.is_powerpoint_installed():
            raise EngineError("NO_ENGINE", "Microsoft PowerPoint is not installed on this Mac.")

        if progress_cb:
            progress_cb(20, f"Invoking Microsoft Office via AppleScript...")

        # Build AppleScript
        in_posix = str(input_path.resolve())
        out_posix = str(output_path.resolve())

        if is_word:
            # Word AppleScript
            # Format codes: wdFormatPDF = 17, wdFormatDocumentDefault = 16 (docx), wdFormatDocument = 0 (doc)
            fmt_code = 17 if target_ext == "pdf" else (16 if target_ext == "docx" else 0)
            script = f'''
            tell application "Microsoft Word"
                set myDoc to open file name "{in_posix}"
                save as myDoc file name "{out_posix}" file format {fmt_code}
                close myDoc saving no
            end tell
            '''
        else:
            # PowerPoint AppleScript
            # ppSaveAsPDF = 32, ppSaveAsDefault = 11 (pptx), ppSaveAsPresentation = 1 (ppt)
            fmt_code = 32 if target_ext == "pdf" else (11 if target_ext == "pptx" else 1)
            script = f'''
            tell application "Microsoft PowerPoint"
                set myPres to open "{in_posix}"
                save in "{out_posix}" as {fmt_code}
                close myPres
            end tell
            '''

        try:
            res = subprocess.run(
                ["osascript", "-e", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                text=True,
            )
        except subprocess.TimeoutExpired:
            raise EngineError("TIMEOUT", "Microsoft Office conversion timed out.")
        except Exception as e:
            raise EngineError("ENGINE_CRASH", f"Office AppleScript execution failed: {e}")

        if res.returncode != 0:
            err = res.stderr.strip()
            raise EngineError("ENGINE_CRASH", f"Office AppleScript error: {err}")

        if not output_path.exists():
            raise EngineError("CORRUPT_FILE", "Microsoft Office did not output the target file.")

        if progress_cb:
            progress_cb(100, "Done")

        return output_path
