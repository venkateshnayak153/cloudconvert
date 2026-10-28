"""
Unit tests for conversion registry and pipeline mappings using standard library unittest.
"""
import unittest
from helper.engines.base import EngineError
from helper.registry import Registry


class TestRegistry(unittest.TestCase):
    def test_registry_pipeline_mappings(self):
        reg = Registry()

        # DOCX -> PDF
        p_docx_pdf = reg.get_pipeline("docx", "pdf")
        self.assertEqual(len(p_docx_pdf), 1)
        self.assertEqual(p_docx_pdf[0].target_ext, "pdf")

        # PDF -> DOCX
        p_pdf_docx = reg.get_pipeline("pdf", "docx")
        self.assertEqual(len(p_pdf_docx), 1)
        self.assertEqual(p_pdf_docx[0].target_ext, "docx")

        # PDF -> DOC (chained pipeline)
        p_pdf_doc = reg.get_pipeline("pdf", "doc")
        self.assertEqual(len(p_pdf_doc), 2)
        self.assertEqual(p_pdf_doc[0].target_ext, "docx")
        self.assertEqual(p_pdf_doc[1].target_ext, "doc")

        # PDF -> PPTX
        p_pdf_pptx = reg.get_pipeline("pdf", "pptx")
        self.assertEqual(len(p_pdf_pptx), 1)
        self.assertEqual(p_pdf_pptx[0].target_ext, "pptx")

        # PDF -> PPT (chained pipeline)
        p_pdf_ppt = reg.get_pipeline("pdf", "ppt")
        self.assertEqual(len(p_pdf_ppt), 2)
        self.assertEqual(p_pdf_ppt[0].target_ext, "pptx")
        self.assertEqual(p_pdf_ppt[1].target_ext, "ppt")

        # DOC -> DOCX and reverse
        p_doc_docx = reg.get_pipeline("doc", "docx")
        self.assertEqual(len(p_doc_docx), 1)
        self.assertEqual(p_doc_docx[0].target_ext, "docx")

    def test_registry_unsupported(self):
        reg = Registry()
        with self.assertRaises(EngineError) as ctx:
            reg.get_pipeline("docx", "docx")
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_TYPE")

        with self.assertRaises(EngineError) as ctx:
            reg.get_pipeline("docx", "png")
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_TYPE")


if __name__ == "__main__":
    unittest.main()
