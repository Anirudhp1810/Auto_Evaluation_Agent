import fitz  # PyMuPDF
from PIL import Image
import io
from tools.ocr_engine import HandwrittenOCREngine

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text from a PDF.
    - If text-based PDF: uses PyMuPDF directly
    - If scanned/image-based: uses Advanced Handwriting OCR (OpenCV + Tesseract)
    """
    doc = fitz.open(pdf_path)
    all_text = ""
    engine = HandwrittenOCREngine(psm=6)

    for page_num, page in enumerate(doc, 1):
        text = page.get_text().strip()

        # If page has very little text, it's likely a scan or image
        if len(text) < 30:
            print(f"Page {page_num}: Using Advanced Handwriting OCR...")
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            result = engine.process_pil_image(img)
            text = result["text"]
            confidence = result["confidence"]
            print(f"Page {page_num} OCR Confidence: {confidence:.2f}%")

        all_text += f"\n--- Page {page_num} ---\n" + text

    return all_text


def extract_from_image(image_path: str) -> str:
    """Extract text from a single image using Advanced Handwriting OCR."""
    engine = HandwrittenOCREngine(psm=6)
    result = engine.extract_from_image_path(image_path)
    return result["text"]
