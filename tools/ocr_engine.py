import cv2
import numpy as np
import pytesseract
import os

# Explicitly mapping Tesseract for Windows users
if os.name == 'nt' and os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
elif os.name == 'nt' and os.path.exists(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'

from PIL import Image
from pdf2image import convert_from_path
import os
import io
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HandwrittenOCREngine:
    def __init__(self, lang='eng', psm=6):
        self.lang = lang
        self.psm = psm
        self.config = f'--oem 3 --psm {self.psm}'

    def preprocess_image(self, image):
        """
        Advanced preprocessing for handwritten text accuracy.
        1. Grayscale
        2. Noise removal (Median blur)
        3. Adaptive Thresholding (Otsu)
        4. Deskewing
        """
        # Convert PIL to OpenCV format
        open_cv_image = np.array(image)
        # Convert RGB to BGR
        if len(open_cv_image.shape) == 3:
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)

        # 1. Grayscale
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)

        # 2. Noise Removal (Median Blur is good for salt & pepper noise)
        # Blur significantly helps with rough edges of handwriting
        blurred = cv2.medianBlur(gray, 3)

        # 3. Thresholding (Otsu's binarization)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 3.1 Dilation (Thickens the handwriting lines slightly to help OCR)
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=1)

        # 4. Deskewing
        deskewed = self.deskew(dilated)
        
        return deskewed

    def deskew(self, image):
        """Detects text orientation and rotates the image to align horizontally."""
        coords = np.column_stack(np.where(image > 0))
        angle = cv2.minAreaRect(coords)[-1]
        
        # minAreaRect returns angle in range [-90, 0)
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return rotated

    def post_process_text(self, text):
        """Cleans up common OCR mistakes in handwritten text."""
        # Remove unwanted noise characters (like scattered periods or single quotes)
        text = re.sub(r'(?m)^\W+', '', text)
        
        # Basic context-blind fixes (careful here)
        # Fix 0/O confusion if surrounded by digits
        text = re.sub(r'(\d)O(\d)', r'\1 0 \2', text)
        # Fix 1/l confusion
        text = re.sub(r'(\d)l(\d)', r'\1 1 \2', text)
        
        # Sentence reconstruction: remove accidental line breaks within sentences
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text) # Handle hyphenated words at line break
        
        return text.strip()

    def get_confidence_score(self, image):
        """Calculates the average confidence score from Tesseract output data."""
        data = pytesseract.image_to_data(image, config=self.config, output_type=pytesseract.Output.DICT)
        confidences = [int(conf) for conf in data['conf'] if conf != -1]
        if not confidences:
            return 0
        return sum(confidences) / len(confidences)

    def extract_from_image_path(self, image_path):
        """Extracts text from a single image file."""
        logger.info(f"Processing image: {image_path}")
        img = Image.open(image_path)
        return self.process_pil_image(img)

    def process_pil_image(self, img):
        """Core logic to process a PIL image and return text + confidence."""
        processed_img = self.preprocess_image(img)
        
        # Convert back to PIL for Tesseract if needed, though pytesseract accepts numpy
        raw_text = pytesseract.image_to_string(processed_img, config=self.config, lang=self.lang)
        confidence = self.get_confidence_score(processed_img)
        
        cleaned_text = self.post_process_text(raw_text)
        
        return {
            "text": cleaned_text,
            "confidence": confidence,
            "raw_text": raw_text
        }

    def extract_from_pdf(self, pdf_path):
        """
        Converts PDF to images and processes each page.
        Returns combined text and metadata.
        """
        logger.info(f"Processing PDF: {pdf_path}")
        try:
            pages = convert_from_path(pdf_path, 300) # 300 DPI for high quality
        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            return {"error": str(e)}

        full_text = ""
        page_results = []
        
        for i, page in enumerate(pages):
            logger.info(f"Processing page {i+1}/{len(pages)}...")
            result = self.process_pil_image(page)
            
            full_text += f"\n--- Page {i+1} ---\n" + result["text"]
            page_results.append({
                "page": i + 1,
                "confidence": result["confidence"],
                "text_length": len(result["text"])
            })
            
        avg_confidence = sum(p["confidence"] for p in page_results) / len(page_results) if page_results else 0
        
        return {
            "text": full_text,
            "avg_confidence": avg_confidence,
            "page_details": page_results
        }

def extract_text_from_handwritten_pdf(file_path):
    """Entry point for the existing pipeline."""
    engine = HandwrittenOCREngine(psm=6) # PSM 6 is generally good for uniform blocks of text
    if file_path.lower().endswith(('.pdf')):
        result = engine.extract_from_pdf(file_path)
        return result.get("text", "")
    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        result = engine.extract_from_image_path(file_path)
        return result.get("text", "")
    return ""
