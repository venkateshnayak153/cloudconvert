"""
Temporary directory management for atomic conversion pipelines.
"""
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


@contextmanager
def managed_temp_dir(prefix: str = "cloudconvert_") -> Generator[Path, None, None]:
    tmp_path = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield tmp_path
    finally:
        try:
            shutil.rmtree(tmp_path, ignore_errors=True)
        except Exception:
            pass
