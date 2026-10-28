"""
File type and signature detection.
Verifies real file signatures against extensions and checks for corruption/encryption.
Optimized for macOS and cross-platform document formats.
"""
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional, Tuple
import zipfile

OLE_MAGIC = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
ZIP_MAGIC = b"PK"
PDF_MAGIC = b"%PDF-"
RTF_MAGIC = b"{\\rtf"
APPLEDOUBLE_MAGIC = b"\x00\x05\x16\x07"


class DetectionError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class DetectionResult:
    format: str  # 'pdf', 'docx', 'doc', 'pptx', 'ppt'
    is_encrypted: bool = False
    is_corrupt: bool = False
    valid_targets: Tuple[str, ...] = ()


def _detect_ole_type(content: bytes, ext: str) -> Tuple[Optional[str], bool]:
    """Inspects OLE compound document streams for Word or PowerPoint signature."""
    # Check for Office encryption stream
    if b"EncryptedPackage" in content:
        return None, True

    # Word OLE files contain 'WordDocument' stream name (UTF-16LE or ASCII in directory)
    if b"WordDocument" in content or b"W\x00o\x00r\x00d\x00D\x00o\x00c\x00u\x00m\x00e\x00n\x00t" in content:
        return "doc", False

    # PowerPoint OLE files contain 'PowerPoint Document' or 'Current User'
    if (
        b"PowerPoint Document" in content
        or b"P\x00o\x00w\x00e\x00r\x00P\x00o\x00i\x00n\x00t" in content
        or b"Current User" in content
    ):
        return "ppt", False

    # If stream directory is ambiguous but it is a valid OLE file with matching extension
    if ext in ("doc", "dot"):
        return "doc", False
    if ext in ("ppt", "pps", "pot"):
        return "ppt", False

    return None, False


def _detect_zip_office_type(path: Path, ext: str) -> Tuple[Optional[str], bool]:
    """Inspects ZIP container for DOCX or PPTX internal structures."""
    try:
        with zipfile.ZipFile(path, "r") as zf:
            namelist = [name.replace("\\", "/").lower() for name in zf.namelist()]
            
            if any(name.startswith("word/") for name in namelist):
                return "docx", False
            if any(name.startswith("ppt/") for name in namelist):
                return "pptx", False
            
            # Check [Content_Types].xml
            for item in zf.namelist():
                if item.lower() == "[content_types].xml":
                    try:
                        ct = zf.read(item).lower()
                        if b"wordprocessingml" in ct or b"msword" in ct:
                            return "docx", False
                        if b"presentationml" in ct or b"powerpoint" in ct:
                            return "pptx", False
                    except Exception:
                        pass

            # Fallback to extension if valid zip
            if ext in ("docx", "docm", "dotx"):
                return "docx", False
            if ext in ("pptx", "pptm", "potx"):
                return "pptx", False

    except zipfile.BadZipFile:
        return None, True
    except Exception:
        return None, True
    return None, False


def _check_pdf_encrypted(content: bytes) -> bool:
    """Checks whether a PDF file is password protected using trailer inspection."""
    # Look for /Encrypt in trailer or xref dictionary
    # Example: /Encrypt 12 0 R or /Encrypt << ... >>
    pattern = re.compile(rb"/Encrypt\s*(\d+\s+\d+\s+R|<<)")
    # Usually in the last 64KB where trailer resides
    tail_sample = content[-65536:] if len(content) > 65536 else content
    if pattern.search(tail_sample):
        return True
    return False


def _check_pdf_valid(content: bytes) -> bool:
    """Checks whether a PDF file contains valid basic structure and EOF marker."""
    if len(content) < 32:
        return False
    # PDF must contain %%EOF marker (anywhere in file, particularly in last 128KB)
    sample = content[-131072:] if len(content) > 131072 else content
    if b"%%EOF" in sample or b"/Root" in content or b"/Catalog" in content:
        return True
    return False


def detect_file(file_path: str) -> DetectionResult:
    """
    Validates file existence, non-emptiness, signature, and supported formats.
    Returns DetectionResult with format and valid target formats.
    Raises DetectionError on mismatch, corruption, or encryption.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise DetectionError("CORRUPT_FILE", f"File not found: {path.name}")

    file_size = path.stat().st_size
    if file_size == 0:
        raise DetectionError("CORRUPT_FILE", "File is empty.")

    # Check for AppleDouble resource fork files (._filename)
    if path.name.startswith("._"):
        raise DetectionError(
            "UNSUPPORTED_TYPE",
            f"'{path.name}' is a macOS system metadata file (AppleDouble). Please drop the original document instead.",
        )

    ext = path.suffix.lower().lstrip(".")

    # Helpful messages for macOS native iWork formats
    if ext == "pages":
        raise DetectionError(
            "UNSUPPORTED_TYPE",
            "Apple Pages (.pages) is not supported directly. Please open your document in Pages and choose File > Export To > Word or PDF.",
        )
    if ext in ("key", "keynote"):
        raise DetectionError(
            "UNSUPPORTED_TYPE",
            "Apple Keynote (.key) is not supported directly. Please open your presentation in Keynote and choose File > Export To > PowerPoint or PDF.",
        )
    if ext in ("numbers", "xlsx", "xls", "csv"):
        raise DetectionError(
            "UNSUPPORTED_TYPE",
            f"Spreadsheets (.{ext}) are out of scope. CloudConvert supports DOC, DOCX, PPT, PPTX, and PDF.",
        )

    allowed_exts = {"pdf", "docx", "doc", "pptx", "ppt", "docm", "dotx", "dot", "pptm", "potx", "rtf"}
    if ext not in allowed_exts:
        raise DetectionError("UNSUPPORTED_TYPE", f"Unsupported file extension: .{ext}")

    try:
        with path.open("rb") as f:
            header = f.read(2048)
    except Exception as e:
        raise DetectionError("CORRUPT_FILE", f"Unable to read file: {e}")

    # Check for AppleDouble binary magic
    if header.startswith(APPLEDOUBLE_MAGIC):
        raise DetectionError(
            "UNSUPPORTED_TYPE",
            "This is a macOS metadata resource fork file, not a valid document.",
        )

    detected_fmt: Optional[str] = None
    is_encrypted = False
    is_corrupt = False

    # 1. PDF Check
    if PDF_MAGIC in header:
        try:
            content = path.read_bytes()
        except Exception as e:
            raise DetectionError("CORRUPT_FILE", f"Unable to read file: {e}")

        if not _check_pdf_valid(content):
            is_corrupt = True
        else:
            detected_fmt = "pdf"
            if _check_pdf_encrypted(content):
                is_encrypted = True

    # 2. OpenXML ZIP (DOCX / PPTX)
    elif header.startswith(ZIP_MAGIC):
        detected_fmt, is_corrupt = _detect_zip_office_type(path, ext)

    # 3. OLE Compound Document (Legacy DOC / PPT)
    elif header.startswith(OLE_MAGIC):
        try:
            content = path.read_bytes()
            detected_fmt, is_encrypted = _detect_ole_type(content, ext)
        except Exception:
            is_corrupt = True

    # 4. RTF Format (often saved with .doc extension)
    elif header.startswith(RTF_MAGIC):
        detected_fmt = "doc"

    else:
        raise DetectionError("UNSUPPORTED_TYPE", f"File signature mismatch for .{ext}")

    if is_encrypted:
        raise DetectionError("PASSWORD_PROTECTED", "This file is password protected.")

    if is_corrupt or not detected_fmt:
        raise DetectionError("CORRUPT_FILE", "This file looks damaged and could not be opened.")

    # Extension mismatch validation:
    # Allow docx/doc cross or pptx/ppt cross if valid format
    if detected_fmt != ext:
        if (detected_fmt in {"doc", "docx"} and ext in {"doc", "docx", "docm", "dotx", "dot", "rtf"}) or \
           (detected_fmt in {"ppt", "pptx"} and ext in {"ppt", "pptx", "pptm", "potx"}):
            pass
        else:
            raise DetectionError(
                "UNSUPPORTED_TYPE",
                f"File content ({detected_fmt.upper()}) does not match extension (.{ext}).",
            )

    valid_targets_map = {
        "pdf": ("docx", "doc", "pptx", "ppt"),
        "docx": ("pdf", "doc"),
        "doc": ("pdf", "docx"),
        "pptx": ("pdf", "ppt"),
        "ppt": ("pdf", "pptx"),
    }

    canonical_fmt = "docx" if detected_fmt in ("docx", "docm", "dotx") else \
                    ("pptx" if detected_fmt in ("pptx", "pptm", "potx") else detected_fmt)

    return DetectionResult(
        format=canonical_fmt,
        is_encrypted=is_encrypted,
        is_corrupt=is_corrupt,
        valid_targets=valid_targets_map.get(canonical_fmt, ()),
    )
