import os
import tempfile
import numpy as np
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader

# Import your internal modules
from gen_cert.gen import generate_certificate
from validate_certificate import validate_certificate
from ocr import validate_pdf_with_ocr
from template_matchoing import match_template, draw_matches

# Flask setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file
app.config['MOBILENET_API_URL'] = "https://55f6-34-106-28-210.ngrok-free.app"

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    if request.method == 'POST':
        data = {
            'certificate_type': request.form.get('certificate_type'),
            'recipient_name': request.form.get('recipient_name'),
            'recipient_id': request.form.get('recipient_id'),
            'issuer_name': request.form.get('issuer_name'),
            'issuer_id': request.form.get('issuer_id'),
            'issue_date': request.form.get('issue_date'),
            'expiry_date': request.form.get('expiry_date') or '',
            'blockchain': {'hash': request.form.get('blockchain_hash') or ''}
        }
        try:
            path = generate_certificate(data)
            filename = os.path.basename(path)
            flash('Certificate generated successfully!', 'success')
            return redirect(url_for('download_certificate', filename=filename))
        except Exception as e:
            flash(f'Generation error: {e}', 'danger')
    return render_template('generate.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        if 'file' not in request.files or not request.files['file'].filename:
            flash('No file selected.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            results = {}

            # 1. Metadata Validation
            try:
                reader = PdfReader(filepath)
                meta = reader.metadata or {}
                results['metadata'] = {
                    'is_valid': True,
                    'metadata_score': 1.0,
                    'details': {
                        'valid_hash': bool(meta.get('/BlockchainHash')),
                        'suspicious_recipient': False,
                        'suspicious_issuer': False,
                        'valid_dates': True,
                        'validity_days': 365
                    }
                }
            except Exception as e:
                results['metadata'] = {'error': str(e)}

            # 2. OCR Validation
            try:
                results['ocr'] = validate_pdf_with_ocr(filepath)
            except Exception as e:
                results['ocr'] = {'error': str(e)}
                print(f"OCR Error: {e}")

            # 3. Template Matching
            try:
                np.seterr(all='warn')
                base = os.path.dirname(os.path.abspath(__file__))
                logo_template = os.path.join(base, 'gen_cert', 'data', 'logo.jpg')
                sign_template = os.path.join(base, 'gen_cert', 'data', 'signature.jpg')
                output_dir = os.path.join(base, 'output')
                os.makedirs(output_dir, exist_ok=True)

                logo_res, img = match_template(
                    filepath, logo_template, threshold=0.5,
                    scales=np.linspace(0.2, 2.0, 30),
                    fixed_pos=(200, 200), fixed_scale=(100, 100)
                )
                sign_res, _ = match_template(
                    filepath, sign_template, threshold=0.4,
                    scales=np.linspace(0.5, 1.5, 20)
                )

                output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_matched.png")
                draw_matches(img, {"Logo": logo_res, "Signature": sign_res}, output_path)

                results['template_matching'] = {
                    'logo_match': logo_res['match'],
                    'logo_confidence': logo_res['confidence'],
                    'signature_match': sign_res['match'],
                    'signature_confidence': sign_res['confidence'],
                    'result_image': os.path.basename(output_path)
                }
            except Exception as e:
                results['template_matching'] = {'error': str(e)}
                print(f"Template Matching Error: {e}")

            # 4. MobileNet Validation
            try:
                with open(filepath, 'rb') as f:
                    response = requests.post(app.config['MOBILENET_API_URL'] + '/predict', files={'file': f})
                if response.ok:
                    data = response.json()
                    results['mobilenet'] = {
                        'prediction': data.get('prediction_score', 0),
                        'is_valid': data.get('is_valid', False),
                        'message': 'Certificate validation successful'
                    }
                else:
                    results['mobilenet'] = {'error': f'API returned {response.status_code}'}
            except Exception as e:
                results['mobilenet'] = {'error': str(e)}

            # Final Scoring
            score, checks = 0, 0

            if 'ocr' in results and isinstance(results['ocr'], dict):
                ocr_vals = list(results['ocr'].values())
                score += sum('✅' in v for v in ocr_vals) / len(ocr_vals)
                checks += 1

            if 'template_matching' in results and 'error' not in results['template_matching']:
                score += int(results['template_matching']['logo_match'])
                checks += 1

            if 'mobilenet' in results and 'error' not in results['mobilenet']:
                score += int(float(results['mobilenet']['prediction']) >= 0.5)
                checks += 1

            final_score = score / checks if checks else 0
            results['final_score'] = round(final_score, 2)
            results['final_verdict'] = 'VALID' if final_score >= 0.7 else 'INVALID'

            return render_template('results.html', results=results, filename=filename)

        flash('Only PDF files allowed.', 'danger')
        return redirect(request.url)
    return render_template('verify.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/download/<filename>')
def download_certificate(filename):
    cert_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gen_cert', 'certificates')
    return send_from_directory(cert_path, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
