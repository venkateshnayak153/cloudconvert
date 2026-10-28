"""
Path utilities for CloudConvert.
Handles non-overwriting output filenames and path normalization.
"""
from pathlib import Path
from typing import Optional


from pathlib import Path
from typing import Optional


class OutputValidationError(Exception):
    """Exception raised when the conversion output fails validation.

    Attributes
    ----------
    code: str
        Short error code identifying the failure reason.
    message: str
        Human‑readable description of the problem.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def resolve_output_path(input_path: str, target_ext: str, out_dir: Optional[str] = None) -> Path:
    """Determine a non‑colliding destination path.

    The function creates a filename ``<stem>_converted.<ext>`` in the same directory as the
    input (or ``out_dir`` if supplied). If that file already exists it appends an incremental
    counter (``_2``, ``_3`` …) until an unused path is found.  The return value is a ``Path``
    object pointing at the chosen location.
    """
    src = Path(input_path).resolve()
    target_ext = target_ext.lstrip(".").lower()

    dest_dir = Path(out_dir).resolve() if out_dir else src.parent
    dest_dir.mkdir(parents=True, exist_ok=True)

    stem = src.stem
    candidate = dest_dir / f"{stem}_converted.{target_ext}"
    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        candidate = dest_dir / f"{stem}_converted_{counter}.{target_ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def validate_output(output_path: Path, ext: str) -> None:
    """Validate that *output_path* looks like a successful conversion.

    The checks performed are lightweight and intended to catch the most common failure
    modes without requiring heavyweight libraries:

    * The file must exist and be larger than zero bytes.
    * For PDFs the first bytes must start with ``%PDF``.
    * For Office formats (``docx``, ``pptx``) and generic ZIP containers the file must begin
      with the ``PK`` signature.

    If any check fails an :class:`OutputValidationError` is raised with an appropriate
    ``code`` (``EMPTY_OUTPUT`` or ``INVALID_OUTPUT``) and a descriptive message.
    """
    if not output_path.exists():
        raise OutputValidationError("EMPTY_OUTPUT", f"Output file {output_path} does not exist.")
    if output_path.stat().st_size == 0:
        raise OutputValidationError("EMPTY_OUTPUT", f"Output file {output_path} is empty.")

    # Read a few bytes to inspect the file header.
    try:
        with open(output_path, "rb") as f:
            header = f.read(4)
    except Exception as e:
        raise OutputValidationError("READ_ERROR", f"Unable to read output file {output_path}: {e}")

    ext = ext.lower()
    if ext == "pdf":
        if not header.startswith(b"%PDF"):
            raise OutputValidationError("INVALID_OUTPUT", f"File {output_path} does not appear to be a valid PDF.")
    elif ext in {"docx", "pptx", "zip"}:
        if not header.startswith(b"PK"):
            raise OutputValidationError(
                "INVALID_OUTPUT", f"File {output_path} does not appear to be a valid {ext.upper()} (missing ZIP signature)."
            )
    # Additional format‑specific checks can be added here.
