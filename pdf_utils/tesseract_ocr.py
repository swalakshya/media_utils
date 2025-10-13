import ocrmypdf
from pdf_utils.ocr_base import OCR, OCRResult

class TesseractOCR(OCR):
    """Concrete implementation using Tesseract via the OCRmyPDF wrapper."""

    def process_to_searchable_pdf(self, input_pdf_path: str, output_pdf_path: str) -> OCRResult:
        """Overrides abstract method to create a new searchable PDF file."""
        print(f"\n--- Running TesseractOCR: Creating Searchable PDF '{output_pdf_path}' ---")
        try:
            ocrmypdf.ocr(
                input_file=input_pdf_path,
                output_file=output_pdf_path,
                language=self.language,
                deskew=True,
                force_ocr=True,
                progress_bar=True
            )
            return OCRResult(
                engine_name="TesseractOCR",
                success=True,
                output_path=output_pdf_path
            )
        except Exception as e:
            return OCRResult(
                engine_name="TesseractOCR",
                success=False,
                text_content=f"Error: {e}"
            )

    def extract_text(self, input_pdf_path: str, page_numbers: list) -> OCRResult:
        """
        Overrides abstract method. Note: Tesseract is better suited for file output
        than raw text extraction, but we implement the abstract method for consistency.
        """
        print("\n--- Running TesseractOCR: Raw Text Extraction (Not recommended for file output) ---")
        # For simplicity, we delegate raw text extraction to the Google Vision subclass,
        # or it can be implemented here using pdf2image + pytesseract.
        return OCRResult(
            engine_name="TesseractOCR",
            success=False,
            text_content="Use 'process_to_searchable_pdf' for Tesseract or 'vision_ocr.py' for raw text extraction."
        )