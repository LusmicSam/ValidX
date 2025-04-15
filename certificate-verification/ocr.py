import fitz  # PyMuPDF
import pytesseract
import cv2
import numpy as np
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from gen_cert.extract_metadata import extract_pdf_metadata
import os
import tempfile

def convert_pdf_to_images(pdf_path):
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img_path = os.path.join(tempfile.gettempdir(), f"page_{page.number}.png")
        pix.save(img_path)
        images.append(img_path)
    return images

def preprocess_image(image_path):
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to load image: {image_path}")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    # Apply adaptive thresholding with optimized parameters
    binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8)
    
    # Apply morphological operations
    kernel = np.ones((1,1), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # Denoise with optimized parameters
    denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
    
    # Save preprocessed image
    preprocessed_path = image_path.replace('.png', '_preprocessed.png')
    cv2.imwrite(preprocessed_path, denoised)
    return preprocessed_path

def extract_text_from_images(image_paths):
    full_text = ""
    for img_path in image_paths:
        # Preprocess image
        processed_img_path = preprocess_image(img_path)
        
        # Configure Tesseract parameters
        custom_config = r'--oem 3 --psm 3'
        
        # Extract text
        text = pytesseract.image_to_string(processed_img_path, config=custom_config)
        full_text += "\n" + text
        
        # Clean up preprocessed image
        if os.path.exists(processed_img_path):
            os.remove(processed_img_path)
    return full_text

def compare_metadata_with_text(metadata, text):
    matches = {}
    check_keys = ["recipient_name", "certificate_type"]
    
    # Normalize text by removing extra whitespace, punctuation and converting to lowercase
    text = ''.join(char.lower() for char in text if char.isalnum() or char.isspace())
    text = ' '.join(text.split())
    
    print("\nDebug OCR Text:")
    print(text)
    print("\nDebug Metadata Values:")
    for key in check_keys:
        print(f"{key}: {metadata.get(key, '')}")
    
    for key in check_keys:
        value = metadata.get(key, "").strip()
        if not value:
            matches[key] = "❌ (Missing in metadata)"
        else:
            # Normalize value and create search pattern
            value = ''.join(char.lower() for char in value if char.isalnum() or char.isspace())
            value = ' '.join(value.split())
            
            # Check for exact or fuzzy matches in the text
            if value in text:
                matches[key] = "✅ Match"
            else:
                # Fallback to word-by-word comparison with improved matching
                value_words = set(value.split())
                text_words = set(text.split())
                
                # Check each word in the value against text words
                matched_words = 0
                for word in value_words:
                    if any(word in text_word or text_word in word for text_word in text_words):
                        matched_words += 1
                
                match_ratio = matched_words / len(value_words)
                if match_ratio >= 0.6:  # Reduced threshold to 60% for better matching
                    matches[key] = "✅ Partial Match"
                else:
                    matches[key] = "❌ Not Found in OCR"
    
    return matches

def validate_pdf_with_ocr(pdf_path):
    print(f"\n📄 Validating PDF: {pdf_path}")

    metadata = extract_pdf_metadata(pdf_path)
    images = convert_pdf_to_images(pdf_path)
    ocr_text = extract_text_from_images(images)

    print("\n🔍 Comparing Metadata with OCR Text...")
    results = compare_metadata_with_text(metadata, ocr_text)

    print("\n📊 Comparison Results:")
    for k, v in results.items():
        print(f"{k}: {v}")

    return results

if __name__ == "__main__":
    # 📝 Replace with your test PDF path
    test_pdf = "gen_cert\certificates\John_Smith_20250413_143514.pdf"
    validate_pdf_with_ocr(test_pdf)
