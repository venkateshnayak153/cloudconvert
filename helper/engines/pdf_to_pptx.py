"""
PDF to PPTX converter engine supporting Image mode and Editable mode.
Uses PyMuPDF (fitz) or pypdf/Pillow and python-pptx.
"""
from pathlib import Path
import tempfile
from typing import Optional

from helper.engines.base import BaseEngine, EngineError, ProgressCallback


class PdfToPptxEngine(BaseEngine):
    name: str = "pdf_to_pptx"

    def is_available(self) -> bool:
        try:
            import pptx  # noqa: F401
            return True
        except ImportError:
            return False

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        target_ext: str,
        progress_cb: Optional[ProgressCallback] = None,
        pptx_mode: str = "image",
        **kwargs,
    ) -> Path:
        if not self.is_available():
            raise EngineError("NO_ENGINE", "python-pptx library is not available.")

        if target_ext.lstrip(".").lower() != "pptx":
            raise EngineError("UNSUPPORTED_TYPE", f"Engine {self.name} only converts to PPTX.")

        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor

        if progress_cb:
            progress_cb(10, f"Initializing presentation in {pptx_mode} mode...")

        prs = Presentation()
        # Remove default slides
        blank_slide_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[0]

        has_pymupdf = False
        try:
            import fitz
            has_pymupdf = True
        except ImportError:
            pass

        if not has_pymupdf:
            # Fallback or error if fitz is not installed
            raise EngineError("NO_ENGINE", "PyMuPDF (fitz) is required for PDF to PPTX conversion.")

        try:
            doc = fitz.open(str(input_path))
            total_pages = len(doc)
            if total_pages == 0:
                raise EngineError("CORRUPT_FILE", "PDF contains no pages.")

            # Set presentation dimensions according to first page
            first_page = doc[0]
            prs.slide_width = Inches(first_page.rect.width / 72.0)
            prs.slide_height = Inches(first_page.rect.height / 72.0)

            with tempfile.TemporaryDirectory(prefix="pdf_pptx_render_") as tmp_dir:
                for idx, page in enumerate(doc):
                    page_num = idx + 1
                    if progress_cb:
                        pct = 15 + int((idx / total_pages) * 75)
                        progress_cb(pct, f"Processing page {page_num} of {total_pages}...")

                    # Create slide
                    slide = prs.slides.add_slide(blank_slide_layout)

                    if pptx_mode == "editable":
                        # Editable mode: Extract text blocks and images
                        blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
                        for b in blocks:
                            if b[6] == 0:  # Text block
                                x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
                                left = Inches(x0 / 72.0)
                                top = Inches(y0 / 72.0)
                                width = Inches(max((x1 - x0) / 72.0, 0.5))
                                height = Inches(max((y1 - y0) / 72.0, 0.3))

                                txBox = slide.shapes.add_textbox(left, top, width, height)
                                tf = txBox.text_frame
                                tf.word_wrap = True
                                tf.text = text.strip()

                        # Extract images on this page
                        image_list = page.get_images(full=True)
                        for img_idx, img_info in enumerate(image_list):
                            xref = img_info[0]
                            base_image = doc.extract_image(xref)
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]

                            img_path = Path(tmp_dir) / f"p{page_num}_img{img_idx}.{image_ext}"
                            img_path.write_bytes(image_bytes)

                            # Find image rect on page if possible
                            rects = page.get_image_rects(xref)
                            if rects:
                                r = rects[0]
                                slide.shapes.add_picture(
                                    str(img_path),
                                    Inches(r.x0 / 72.0),
                                    Inches(r.y0 / 72.0),
                                    Inches(r.width / 72.0),
                                    Inches(r.height / 72.0),
                                )
                    else:
                        # Image mode: Render page at 150 DPI for high visual fidelity
                        zoom = 150.0 / 72.0
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat, alpha=False)

                        img_path = Path(tmp_dir) / f"page_{page_num}.png"
                        pix.save(str(img_path))

                        # Insert full bleed
                        slide.shapes.add_picture(
                            str(img_path),
                            Inches(0),
                            Inches(0),
                            prs.slide_width,
                            prs.slide_height,
                        )

            doc.close()

            if progress_cb:
                progress_cb(92, "Saving PowerPoint presentation...")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            prs.save(str(output_path))

            if progress_cb:
                progress_cb(100, "Done")

            return output_path
        except Exception as e:
            raise EngineError("ENGINE_CRASH", f"PDF to PPTX conversion failed: {e}")
