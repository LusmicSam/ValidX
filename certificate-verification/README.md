# Certificate Verification System

A robust blockchain-based certificate verification system with advanced OCR capabilities, IPFS integration, and ML-based validation. This system ensures the authenticity and integrity of digital certificates through multiple validation layers.

## Features

- **Blockchain Integration**: Secure certificate storage and verification using blockchain technology
- **OCR Verification**: Advanced text extraction and validation using Tesseract OCR
- **Template Matching**: Logo and signature verification using computer vision
- **ML-based Validation**: Certificate validation using MobileNetV2
- **IPFS Integration**: Decentralized storage of certificates using IPFS
- **Web Interface**: User-friendly interface for certificate generation and verification

## Tech Stack

- **Backend**: Python, Flask
- **Computer Vision**: OpenCV, PyMuPDF
- **OCR**: Tesseract
- **Machine Learning**: TensorFlow, MobileNetV2
- **Blockchain**: Solidity
- **Storage**: IPFS (Pinata)

## Installation

1. Clone the repository
2. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Tesseract OCR:
   - Windows: Download and install from [Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   - Update the Tesseract path in `ocr.py` if necessary

## Usage

1. Start the Flask application:
   ```bash
   python app.py
   ```
2. Access the web interface at `http://localhost:5000`
3. Use the following features:
   - Generate new certificates
   - Upload certificates for verification
   - View verification results with detailed analysis

## Verification Process

The system employs a multi-layer verification approach:
1. Metadata Validation
2. OCR Text Verification
3. Template Matching
4. ML-based Certificate Validation
5. Blockchain Hash Verification

## Project Structure

- `app.py`: Main Flask application
- `ocr.py`: OCR and text verification
- `blockchain/`: Blockchain integration
- `gen_cert/`: Certificate generation
- `models/`: ML models
- `templates/`: Web interface templates

## Contributors

- **Priyatosh**
  - Blockchain Integration
  - Smart Contract Development

- **Arpit Yadav**
  - ML Model Development
  - Template Matching

## License

MIT License

## Security

- All certificates are cryptographically signed
- Blockchain ensures immutability
- Multi-factor verification prevents forgery