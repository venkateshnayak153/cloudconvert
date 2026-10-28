"""
LibreOffice engine adapter.
Invokes headless LibreOffice in an isolated user profile.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from helper.engines.base import BaseEngine, EngineError, ProgressCallback


class LibreOfficeEngine(BaseEngine):
    name: str = "libreoffice"

    def _find_binary(self) -> Optional[str]:
        # Check PATH
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if soffice:
            return soffice

        # macOS standard paths
        if sys.platform == "darwin":
            mac_paths = [
                "/Applications/LibreOffice.app/Contents/MacOS/soffice",
                os.path.expanduser("~/Applications/LibreOffice.app/Contents/MacOS/soffice"),
            ]
            for p in mac_paths:
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    return p

        # Windows standard paths
        elif sys.platform == "win32":
            win_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
            for p in win_paths:
                if os.path.isfile(p):
                    return p

        # Linux standard paths
        else:
            linux_paths = ["/usr/bin/soffice", "/usr/bin/libreoffice", "/usr/local/bin/soffice"]
            for p in linux_paths:
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    return p

        return None

    def is_available(self) -> bool:
        return self._find_binary() is not None

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        target_ext: str,
        progress_cb: Optional[ProgressCallback] = None,
        timeout_seconds: int = 300,
        **kwargs,
    ) -> Path:
        binary = self._find_binary()
        if not binary:
            raise EngineError("NO_ENGINE", "LibreOffice is not installed.")

        target_ext = target_ext.lstrip(".").lower()
        if progress_cb:
            progress_cb(15, "Starting LibreOffice engine...")

        # Create isolated temporary profile and output directory
        with tempfile.TemporaryDirectory(prefix="libreoffice_profile_") as profile_dir, \
             tempfile.TemporaryDirectory(prefix="libreoffice_out_") as tmp_out_dir:

            profile_uri = Path(profile_dir).resolve().as_uri()

            cmd = [
                binary,
                "--headless",
                "--norestore",
                "--invisible",
                f"-env:UserInstallation={profile_uri}",
                "--convert-to",
                target_ext,
                "--outdir",
                str(tmp_out_dir),
                str(input_path),
            ]

            if progress_cb:
                progress_cb(40, f"Converting {input_path.name} to {target_ext.upper()}...")

            try:
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout_seconds,
                    text=True,
                )
            except subprocess.TimeoutExpired:
                raise EngineError("TIMEOUT", "The conversion took too long and was stopped.")
            except Exception as e:
                raise EngineError("ENGINE_CRASH", f"LibreOffice failed to run: {e}")

            if proc.returncode != 0:
                err_msg = proc.stderr.strip() or proc.stdout.strip()
                raise EngineError("ENGINE_CRASH", f"LibreOffice conversion error: {err_msg}")

            # Locate converted file in tmp_out_dir
            candidates = list(Path(tmp_out_dir).glob(f"*.{target_ext}"))
            if not candidates:
                raise EngineError("CORRUPT_FILE", "LibreOffice did not produce an output file.")

            converted = candidates[0]
            if progress_cb:
                progress_cb(90, "Finalizing output...")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(converted), str(output_path))

            if progress_cb:
                progress_cb(100, "Done")

            return output_path
