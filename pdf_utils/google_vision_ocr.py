from google.cloud import vision
from pdf2image import convert_from_path
from io import BytesIO
from ocr_base import OCR, OCRResult

class GoogleVisionOCR(OCR):
    """Concrete implementation using Google Cloud Vision API."""

    def process_to_searchable_pdf(self, input_pdf_path: str, output_pdf_path: str) -> OCRResult:
        """Overrides abstract method. Note: Vision API returns text, not a PDF file."""
        return OCRResult(
            engine_name="GoogleVisionOCR",
            success=False,
            text_content="Google Vision API primarily extracts text, it cannot create the final searchable PDF file."
        )

    def extract_text(self, input_pdf_path: str, page_numbers: list) -> OCRResult:
        """Overrides abstract method to perform high-accuracy raw text extraction."""
        print(f"\n--- Running GoogleVisionOCR: Raw Text Extraction on pages {page_numbers} ---")

        # 1. Convert PDF pages to PIL Images in memory
        images = convert_from_path(
            input_pdf_path,
            first_page=page_numbers[0],
            last_page=page_numbers[-1],
            dpi=300
        )

        client = vision.ImageAnnotatorClient()
        full_text = []

        # 2. Perform OCR on each image
        for i, img in enumerate(images):
            # Convert PIL Image to Bytes for the API call
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            content = img_byte_arr.getvalue()

            image = vision.Image(content=content)

            # Use Document Text Detection for dense multi-language documents
            response = client.document_text_detection(image=image)

            text = response.full_text_annotation.text
            full_text.append(f"\n--- Page {page_numbers[0] + i} Text ---\n{text}")

        return OCRResult(
            engine_name="GoogleVisionOCR",
            success=True,
            text_content="".join(full_text)
        )