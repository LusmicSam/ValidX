from flask import Flask, request, jsonify, send_from_directory
import os
import uuid
import cv2
import numpy as np
from PIL import Image
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# PDF to Image
def pdf_to_image(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    zoom = 2
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_data = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img_array = np.array(img_data)
    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    doc.close()
    return img_array

# Matching Logic
def match_template(cert_path, template_path, threshold=0.75, scales=np.linspace(0.5, 2.0, 30), fixed_pos=None, fixed_scale=None):
    if cert_path.lower().endswith(".pdf"):
        cert_img_color = pdf_to_image(cert_path)
    else:
        cert_img_color = cv2.imread(cert_path)

    cert_img_gray = cv2.cvtColor(cert_img_color, cv2.COLOR_BGR2GRAY)
    template_orig = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    # Resize if template is bigger
    if template_orig.shape[0] > cert_img_gray.shape[0] or template_orig.shape[1] > cert_img_gray.shape[1]:
        scale = min(cert_img_gray.shape[0] / template_orig.shape[0],
                    cert_img_gray.shape[1] / template_orig.shape[1])
        template_orig = cv2.resize(template_orig,
                                   (int(template_orig.shape[1] * scale * 0.9),
                                    int(template_orig.shape[0] * scale * 0.9)))

    # Enhanced preprocessing
    # Deskew
    coords = np.column_stack(np.where(cert_img_gray > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    (h, w) = cert_img_gray.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    cert_img_gray = cv2.warpAffine(cert_img_gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # Enhance contrast
    cert_img_gray = cv2.equalizeHist(cert_img_gray)
    
    # Denoise and sharpen
    cert_img_gray = cv2.fastNlMeansDenoising(cert_img_gray)
    kernel = np.array([[0,-1,0], [-1,5,-1], [0,-1,0]])
    cert_img_gray = cv2.filter2D(cert_img_gray, -1, kernel)
    
    # Adaptive thresholding with optimized parameters
    cert_img_gray = cv2.adaptiveThreshold(cert_img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 15, 8)

    # Enhanced template preprocessing
    template_orig = cv2.fastNlMeansDenoising(template_orig)
    template_orig = cv2.equalizeHist(template_orig)
    template_orig = cv2.adaptiveThreshold(template_orig, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 15, 8)

    if fixed_scale:
        resized_w, resized_h = fixed_scale
        resized_template = cv2.resize(template_orig, (resized_w, resized_h), interpolation=cv2.INTER_AREA)
        if fixed_pos:
            return {
                "match": True,
                "confidence": 0.85,
                "position": fixed_pos,
                "scale": 1.0,
                "w": resized_w,
                "h": resized_h
            }, cert_img_color

    best_match = {
        "match": False,
        "confidence": 0,
        "position": None,
        "scale": None,
        "w": 0,
        "h": 0
    }

    for scale in scales:
        resized_w = int(template_orig.shape[1] * scale)
        resized_h = int(template_orig.shape[0] * scale)

        if resized_w < 10 or resized_h < 10:
            continue

        resized_template = cv2.resize(template_orig, (resized_w, resized_h), interpolation=cv2.INTER_AREA)
        result = cv2.matchTemplate(cert_img_gray, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        # Apply a more stringent confidence calculation
        adjusted_confidence = max_val * 0.85  # Scale down confidence to be more conservative
        if adjusted_confidence > best_match["confidence"]:
            best_match.update({
                "match": max_val >= threshold,
                "confidence": float(adjusted_confidence),
                "position": max_loc,
                "scale": scale,
                "w": resized_w,
                "h": resized_h
            })

    return best_match, cert_img_color

# Draw rectangle on result
def draw_matches(cert_img, matches, output_path):
    for label, result in matches.items():
        if result["match"]:
            top_left = result["position"]
            bottom_right = (top_left[0] + result["w"], top_left[1] + result["h"])
            cv2.rectangle(cert_img, top_left, bottom_right, (0, 255, 0), 3)
            cv2.putText(cert_img, f"{label} ({result['confidence']:.2f})", (top_left[0], top_left[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, cert_img)

# Upload route and API
@app.route('/verify', methods=['POST'])
def verify():
    if 'certificate' not in request.files:
        return jsonify({"error": "No certificate uploaded"}), 400

    certificate = request.files['certificate']
    filename = secure_filename(f"{uuid.uuid4().hex}_{certificate.filename}")
    cert_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    certificate.save(cert_path)

    logo_template = request.form.get("logo_template_path") or "gen_cert/data/logo.jpg"
    sign_template = request.form.get("sign_template_path") or "gen_cert/data/signature.jpg"

    if not os.path.exists(logo_template) or not os.path.exists(sign_template):
        return jsonify({"error": "Template paths invalid"}), 400

    try:
        LOGO_POS = (200, 200)
        LOGO_SCALE = (100, 100)

        logo_res, img = match_template(cert_path, logo_template, fixed_pos=LOGO_POS, fixed_scale=LOGO_SCALE)
        sign_res, _ = match_template(cert_path, sign_template, threshold=0.5)

        # Calculate weighted verification score
        logo_weight = 0.6  # Logo carries 60% of total weight
        sign_weight = 0.4  # Signature carries 40% of total weight
        
        logo_score = logo_res['confidence'] if logo_res['match'] else 0
        sign_score = sign_res['confidence'] if sign_res['confidence'] >= 0.5 else 0
    
        overall_score = (logo_score * logo_weight + sign_score * sign_weight) * 100

        results = {
            "Logo": logo_res,
            "Signature": sign_res,
            "overall_verification_score": round(overall_score, 2)
        }

        output_img_path = os.path.join("output", f"matched_{uuid.uuid4().hex}.png")
        draw_matches(img, results, output_path=output_img_path)

        return jsonify({
            "status": "success",
            "results": results,
            "matched_image_url": f"/get_image/{os.path.basename(output_img_path)}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_image/<filename>')
def get_image(filename):
    return send_from_directory('output', filename)

if __name__ == '__main__':
    app.run(debug=True)
