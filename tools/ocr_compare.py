import sys
import os
from PIL import Image
import pytesseract
import cv2
import numpy as np

# Add parent directory to path if needed to import tools
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from tools.ocr_engine import HandwrittenOCREngine

def compare_ocr(file_path):
    """Compares raw Tesseract output with preprocessed output."""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    print(f"\n{'='*50}")
    print(f"OCR COMPARISON: {os.path.basename(file_path)}")
    print(f"{'='*50}\n")

    # 1. Raw Tesseract
    img = Image.open(file_path)
    raw_text = pytesseract.image_to_string(img, config='--oem 3 --psm 6')
    
    # 2. Preprocessed Tesseract
    engine = HandwrittenOCREngine(psm=6)
    result = engine.extract_from_image_path(file_path)
    
    print("--- RAW TESSERACT OUTPUT ---")
    print(raw_text if raw_text.strip() else "[No text detected]")
    print("\n" + "-"*30 + "\n")
    
    print("--- PREPROCESSED TESSERACT OUTPUT ---")
    print(result["text"] if result["text"].strip() else "[No text detected]")
    print(f"\n[Confidence Score: {result['confidence']:.2f}%]")
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ocr_compare.py <image_path>")
    else:
        compare_ocr(sys.argv[1])
