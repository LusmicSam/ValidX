from PyPDF2 import PdfReader
from datetime import datetime
import ast
import re
import os

def convert_pdf_date(pdf_date):
    """Convert PDF date format D:YYYYMMDDHHMMSS to standard YYYY-MM-DD"""
    try:
        if pdf_date.startswith('D:'):
            return datetime.strptime(pdf_date[2:10], '%Y%m%d').strftime('%Y-%m-%d')
        return datetime.strptime(pdf_date[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
    except:
        return None

def extract_pdf_metadata(pdf_path):
    """Extract and structure metadata from a PDF certificate"""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")

    reader = PdfReader(pdf_path)
    metadata = reader.metadata or {}

    # Extract and clean metadata fields
    result = {
        'certificate_type': metadata.get('/Title', '').strip(),
        'recipient_name': metadata.get('/Subject', '').replace('Certificate for ', '').strip(),
        'recipient_id': metadata.get('/RecipientID', '').strip(),
        'issuer_name': metadata.get('/Author', '').strip(),
        'issuer_id': metadata.get('/IssuerID', '').strip(),
        'issue_date': convert_pdf_date(metadata.get('/IssueDate', '')),
        'expiry_date': convert_pdf_date(metadata.get('/ExpiryDate', '')),
        'blockchain': str({'hash': metadata.get('/BlockchainHash', '').strip()}),
    }

    return result

# Optional for standalone testing
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python extract_metadata.py <path_to_pdf>")
    else:
        pdf_path = sys.argv[1]
        try:
            data = extract_pdf_metadata(pdf_path)
            print(" Extracted Certificate Metadata:")
            for key, val in data.items():
                print(f"{key}: {val}")
        except Exception as e:
            print(f"Error: {e}")
