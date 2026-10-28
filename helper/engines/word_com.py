"""
Windows COM automation engine for Microsoft Word and PowerPoint.
"""
from pathlib import Path
import sys
from typing import Optional

from helper.engines.base import BaseEngine, EngineError, ProgressCallback


class WindowsCOMEngine(BaseEngine):
    name: str = "office_com"

    def is_available(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import win32com.client
            return True
        except ImportError:
            return False

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        target_ext: str,
        progress_cb: Optional[ProgressCallback] = None,
        timeout_seconds: int = 300,
        **kwargs,
    ) -> Path:
        if sys.platform != "win32":
            raise EngineError("NO_ENGINE", "Windows COM engine only runs on Windows.")

        try:
            import win32com.client
            import pythoncom
        except ImportError:
            raise EngineError("NO_ENGINE", "pywin32 is not installed.")

        src_ext = input_path.suffix.lower().lstrip(".")
        target_ext = target_ext.lstrip(".").lower()

        is_word = src_ext in {"doc", "docx"} or (src_ext == "pdf" and target_ext in {"doc", "docx"})
        is_ppt = src_ext in {"ppt", "pptx"} or (src_ext == "pdf" and target_ext in {"ppt", "pptx"})

        in_str = str(input_path.resolve())
        out_str = str(output_path.resolve())

        pythoncom.CoInitialize()
        try:
            if is_word:
                if progress_cb:
                    progress_cb(20, "Launching Microsoft Word COM...")
                # wdFormatPDF = 17, wdFormatXMLDocument = 12 (docx), wdFormatDocument = 0 (doc)
                fmt = 17 if target_ext == "pdf" else (12 if target_ext == "docx" else 0)
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                word.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
                try:
                    doc = word.Documents.Open(in_str, ReadOnly=True, ConfirmConversions=False)
                    if progress_cb:
                        progress_cb(50, "Saving document...")
                    doc.SaveAs2(out_str, FileFormat=fmt)
                    doc.Close(SaveChanges=False)
                finally:
                    word.Quit()
            elif is_ppt:
                if progress_cb:
                    progress_cb(20, "Launching Microsoft PowerPoint COM...")
                # ppSaveAsPDF = 32, ppSaveAsOpenXMLPresentation = 24 (pptx), ppSaveAsPresentation = 1 (ppt)
                fmt = 32 if target_ext == "pdf" else (24 if target_ext == "pptx" else 1)
                ppt = win32com.client.DispatchEx("PowerPoint.Application")
                ppt.Visible = True  # Required for PowerPoint COM object model, but can be minimized
                ppt.WindowState = 2  # ppWindowMinimized
                try:
                    pres = ppt.Presentations.Open(in_str, ReadOnly=True, Untitled=False, WithWindow=False)
                    if progress_cb:
                        progress_cb(50, "Saving presentation...")
                    pres.SaveAs(out_str, fmt)
                    pres.Close()
                finally:
                    ppt.Quit()
            else:
                raise EngineError("UNSUPPORTED_TYPE", f"Unsupported conversion from {src_ext} to {target_ext}")

            if not output_path.exists():
                raise EngineError("CORRUPT_FILE", "Office COM did not generate the target file.")

            if progress_cb:
                progress_cb(100, "Done")

            return output_path
        except Exception as e:
            raise EngineError("ENGINE_CRASH", f"Office COM error: {e}")
        finally:
            pythoncom.CoUninitialize()
