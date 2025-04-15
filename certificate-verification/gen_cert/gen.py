import os
from PIL import Image, ImageDraw, ImageFont
import qrcode
from datetime import datetime
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from io import BytesIO
from PyPDF2 import PdfWriter, PdfReader

# Configuration
TEMPLATE_PATH = 'gen_cert/data/template.png'
WATERMARK_PATH = 'gen_cert/data/watermark.png'
OUTPUT_DIR = 'gen_cert/certificates'
LOGO_PATH = 'gen_cert/data/logo.jpg'
SIGNATURE_PATH = 'gen_cert/data/signature.jpg'

# Font settings
FONT_PATH = 'gen_cert/data/Arial.ttf'
TITLE_SIZE = 20
NAME_SIZE = 30
DETAIL_SIZE = 24

# Position coordinates (adjust as per your template)
TITLE_POS = (150, 130)
NAME_POS = (150, 250)
ISSUER_POS = (200, 400)
DATE_POS = (530, 450)
QR_POS = (570, 300)
LOGO_POS = (100, 100)
SIGNATURE_POS = (200, 400)

def validate_date(date_text):
    """Validate and return date in YYYY-MM-DD format"""
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None

def get_certificate_details():
    """Get certificate details from user input"""
    details = {}

    details['certificate_type'] = input("Enter certificate type: ")
    details['recipient_name'] = input("Enter recipient name: ")
    details['recipient_id'] = input("Enter recipient ID: ")
    details['issuer_name'] = input("Enter issuer name: ")
    details['issuer_id'] = input("Enter issuer ID: ")

    while True:
        issue_date = input("Enter issue date (YYYY-MM-DD): ")
        valid = validate_date(issue_date)
        if valid:
            details['issue_date'] = valid
            break
        print("Invalid date format. Please use YYYY-MM-DD.")

    expiry_date = input("Enter expiry date (YYYY-MM-DD) or press Enter to skip: ")
    if expiry_date:
        valid = validate_date(expiry_date)
        if valid:
            details['expiry_date'] = valid
        else:
            print("Invalid expiry date. Skipping.")
            details['expiry_date'] = ""
    else:
        details['expiry_date'] = ""

    blockchain_hash = input("Enter blockchain hash or press Enter to skip: ")
    details['blockchain'] = {"hash": blockchain_hash} if blockchain_hash else {"hash": ""}

    return details

def generate_certificate(data):
    """Generate a certificate using the provided data"""
    # Load certificate template
    cert = Image.open(TEMPLATE_PATH).convert('RGBA')

    # Add logo
    logo = Image.open(LOGO_PATH).convert('RGBA')
    logo.thumbnail((50, 50), Image.LANCZOS)
    logo_layer = Image.new('RGBA', cert.size, (0, 0, 0, 0))
    logo_layer.paste(logo, LOGO_POS, logo)
    cert = Image.alpha_composite(cert, logo_layer)

    # Add signature
    signature = Image.open(SIGNATURE_PATH).convert('RGBA')
    signature.thumbnail((150, 100), Image.LANCZOS)
    signature_layer = Image.new('RGBA', cert.size, (0, 0, 0, 0))
    signature_layer.paste(signature, SIGNATURE_POS, signature)
    cert = Image.alpha_composite(cert, signature_layer)

    # Add text
    draw = ImageDraw.Draw(cert)

    title_font = ImageFont.truetype(FONT_PATH, TITLE_SIZE)
    name_font = ImageFont.truetype(FONT_PATH, NAME_SIZE)
    detail_font = ImageFont.truetype(FONT_PATH, DETAIL_SIZE)

    draw.text(TITLE_POS, data['certificate_type'], fill='black', font=title_font)
    draw.text(NAME_POS, data['recipient_name'], fill='black', font=name_font)

    date_text = f"Issued: {data['issue_date']}"
    if data['expiry_date']:
        date_text += f"\nExpires: {data['expiry_date']}"
    draw.text(DATE_POS, date_text, fill='black', font=detail_font)

    # Add QR Code
    if data['blockchain']['hash']:
        qr = qrcode.make(data['blockchain']['hash'])
        qr_image = qr.get_image().convert('RGBA')
        qr_image.thumbnail((150, 150), Image.LANCZOS)
        qr_layer = Image.new('RGBA', cert.size, (0, 0, 0, 0))
        qr_layer.paste(qr_image, QR_POS, qr_image)
        cert = Image.alpha_composite(cert, qr_layer)

    # Add watermark
    watermark = Image.open(WATERMARK_PATH).convert('RGBA')
    watermark = watermark.resize(cert.size, Image.LANCZOS)
    watermark.putdata([
        (r, g, b, 50) for (r, g, b, a) in watermark.getdata()
    ])
    cert = Image.alpha_composite(cert, watermark)

    # Convert to RGB before saving
    cert = cert.convert('RGB')

    # Save as temporary PNG first
    temp_buffer = BytesIO()
    cert.save(temp_buffer, format='PNG', resolution=300.0)
    temp_buffer.seek(0)

    # Create output directory and filename
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = "".join(c for c in data['recipient_name'] if c.isalnum() or c in (' ', '_')).rstrip()
    filename = f"{safe_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(OUTPUT_DIR, filename)
    
    # Create temporary PDF with image
    temp_pdf = os.path.join(OUTPUT_DIR, "temp.pdf")
    page_width, page_height = cert.size
    c = canvas.Canvas(temp_pdf, pagesize=(page_width, page_height))
    c.drawImage(ImageReader(temp_buffer), 0, 0, page_width, page_height)
    c.save()
    
    # Add metadata using PyPDF2
    reader = PdfReader(temp_pdf)
    writer = PdfWriter()
    
    # Add the page
    writer.add_page(reader.pages[0])
    
    # Add metadata
    metadata = {
        "/Title": data['certificate_type'],
        "/Author": data['issuer_name'],
        "/Subject": f"Certificate for {data['recipient_name']}",
        "/Keywords": f"{data['certificate_type']}, {data['recipient_name']}, {data['recipient_id']}, {data['issuer_name']}, {data['issuer_id']}",
        "/Producer": "Certificate Generator v1.0",
        "/CreationDate": datetime.now().strftime("D:%Y%m%d%H%M%S"),
        "/ModDate": datetime.now().strftime("D:%Y%m%d%H%M%S"),
        "/Creator": "Certificate Generator",
        "/RecipientID": data['recipient_id'],
        "/IssuerID": data['issuer_id'],
        "/IssueDate": data['issue_date'],
        "/ExpiryDate": data['expiry_date'] if data['expiry_date'] else "No Expiry",
        "/BlockchainHash": data['blockchain']['hash'] if data['blockchain']['hash'] else "No Hash"
    }
    writer.add_metadata(metadata)
    
    # Save final PDF
    with open(pdf_path, "wb") as output_file:
        writer.write(output_file)
    
    # Remove temporary PDF
    os.remove(temp_pdf)
    
    return pdf_path

def main():
    print("Please enter the certificate details:")
    certificate_data = get_certificate_details()
    
    pdf_path = generate_certificate(certificate_data)
    print(f"\n✅ Certificate generated successfully!")
    print(f"📄 File saved at: {os.path.abspath(pdf_path)}")
    return pdf_path

if __name__ == '__main__':
    main()