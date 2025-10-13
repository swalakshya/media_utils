from abc import ABC, abstractmethod

# Define the expected output structure for extracted text
class OCRResult:
    def __init__(self, engine_name, success, text_content=None, output_path=None):
        self.engine_name = engine_name
        self.success = success
        self.text_content = text_content
        self.output_path = output_path

    def __str__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"[{self.engine_name} Result] Status: {status}, Output: {self.output_path or 'Text in memory'}"

class OCR(ABC):
    """Abstract Base Class for all OCR processors."""

    def __init__(self, language: str = 'hin'):
        self.language = language

    @abstractmethod
    def process_to_searchable_pdf(self, input_pdf_path: str, output_pdf_path: str) -> OCRResult:
        """
        Processes an image-only PDF and returns a new searchable PDF file.
        This is the primary method that the Tesseract subclass will implement.
        """
        pass

    @abstractmethod
    def extract_text(self, input_pdf_path: str, page_numbers: list) -> OCRResult:
        """
        Extracts raw text content from specified pages of a PDF.
        This method is ideal for the Google Vision API subclass.
        """
        pass