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
    
    # Resize image if too large (helps with OCR accuracy)
    max_dimension = 2000
    height, width = img.shape[:2]
    if max(height, width) > max_dimension:
        scale = max_dimension / max(height, width)
        img = cv2.resize(img, None, fx=scale, fy=scale)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply bilateral filter to reduce noise while preserving edges
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Apply contrast enhancement with optimized parameters
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    # Apply Otsu's thresholding
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Apply morphological operations to clean up text
    kernel = np.ones((2,2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    # Save preprocessed image
    preprocessed_path = image_path.replace('.png', '_preprocessed.png')
    cv2.imwrite(preprocessed_path, binary)
    return preprocessed_path

def extract_text_from_images(image_paths):
    full_text = ""
    for img_path in image_paths:
        try:
            # Preprocess image
            processed_img_path = preprocess_image(img_path)
            
            # Configure Tesseract parameters for better accuracy
            custom_config = r'--oem 3 --psm 1 -l eng --dpi 300'
            
            # Extract text with multiple PSM modes for better results
            psm_modes = [1, 3, 6]  # Auto, Block, Uniform block
            text = ""
            for psm in psm_modes:
                config = f'--oem 3 --psm {psm} -l eng --dpi 300'
                text += pytesseract.image_to_string(processed_img_path, config=config)
            
            # Clean and normalize extracted text
            text = ' '.join(text.split())  # Remove extra whitespace
            full_text += "\n" + text
            
        except Exception as e:
            print(f"Error processing {img_path}: {str(e)}")
            continue
        finally:
            # Clean up preprocessed image
            if os.path.exists(processed_img_path):
                os.remove(processed_img_path)
    return full_text

def compare_metadata_with_text(metadata, text):
    matches = {}
    check_keys = ["recipient_name", "certificate_type"]
    
    # Enhanced text normalization
    def normalize_text(input_text):
        # Convert to lowercase and remove special characters
        text = ''.join(char.lower() for char in input_text if char.isalnum() or char.isspace())
        # Remove extra whitespace and split into words
        words = text.split()
        # Remove common OCR errors and short words (likely noise)
        words = [w for w in words if len(w) > 1]
        return ' '.join(words)
    
    # Normalize OCR text
    normalized_text = normalize_text(text)
    
    print("\nDebug OCR Text:")
    print(normalized_text)
    print("\nDebug Metadata Values:")
    for key in check_keys:
        print(f"{key}: {metadata.get(key, '')}")
    
    for key in check_keys:
        value = metadata.get(key, "").strip()
        if not value:
            matches[key] = "❌ (Missing in metadata)"
            continue
            
        # Normalize metadata value
        normalized_value = normalize_text(value)
        value_words = normalized_value.split()
        
        # First try exact match
        if normalized_value in normalized_text:
            matches[key] = "✅ Match"
            continue
            
        # Then try word-by-word fuzzy matching
        text_words = normalized_text.split()
        matched_words = 0
        total_similarity = 0
        
        for word in value_words:
            # Check for substring matches and calculate similarity
            best_similarity = 0
            for text_word in text_words:
                # Calculate Levenshtein distance-based similarity
                max_len = max(len(word), len(text_word))
                if max_len == 0:
                    continue
                    
                distance = sum(1 for i in range(min(len(word), len(text_word)))
                               if word[i] != text_word[i])
                similarity = 1 - (distance / max_len)
                
                # Check for substring containment
                if word in text_word or text_word in word:
                    similarity = max(similarity, 0.8)  # Boost similarity for substring matches
                    
                best_similarity = max(best_similarity, similarity)
            
            if best_similarity >= 0.7:  # Threshold for considering a word matched
                matched_words += 1
                total_similarity += best_similarity
        
        # Calculate final match score
        if matched_words > 0:
            match_score = (matched_words / len(value_words)) * (total_similarity / matched_words)
            
            if match_score >= 0.8:
                matches[key] = "✅ Match"
            elif match_score >= 0.6:
                matches[key] = "✅ Partial Match"
            else:
                matches[key] = "❌ Not Found in OCR"
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
    test_pdf = "gen_cert/certificates/shiv_20250413_185807.pdf"
    validate_pdf_with_ocr(test_pdf)
