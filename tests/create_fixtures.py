"""
Fixture generator for CloudConvert tests.
"""
from pathlib import Path
import zipfile

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


def create_all_fixtures():
    # 1. Valid sample.pdf
    pdf_path = FIXTURES_DIR / "sample.pdf"
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n185\n%%EOF"
    )
    pdf_path.write_bytes(pdf_content)

    # 2. Encrypted sample
    enc_path = FIXTURES_DIR / "encrypted.pdf"
    enc_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"trailer\n<< /Encrypt << /V 2 /R 3 >> /Root 1 0 R >>\n%%EOF"
    )
    enc_path.write_bytes(enc_content)

    # 3. Corrupt PDF
    corrupt_path = FIXTURES_DIR / "corrupt.pdf"
    corrupt_path.write_bytes(b"%PDF-1.4 broken non-pdf bytes...")

    # 4. Wrong extension (a PDF named wrong_extension.docx)
    wrong_ext = FIXTURES_DIR / "wrong_extension.docx"
    wrong_ext.write_bytes(pdf_content)

    # 5. Valid DOCX fixture (Zip with Word Content_Types)
    docx_path = FIXTURES_DIR / "sample.docx"
    with zipfile.ZipFile(docx_path, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        zf.writestr("word/document.xml", '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Hello CloudConvert</w:t></w:r></w:p></w:body></w:document>')

    # 6. Valid PPTX fixture (Zip with PPT Content_Types)
    pptx_path = FIXTURES_DIR / "sample.pptx"
    with zipfile.ZipFile(pptx_path, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
            "</Types>",
        )
        zf.writestr("ppt/presentation.xml", '<?xml version="1.0"?><p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"></p:presentation>')

    print(f"Generated test fixtures in {FIXTURES_DIR}")


if __name__ == "__main__":
    create_all_fixtures()
