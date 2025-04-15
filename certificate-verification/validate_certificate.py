import os
import numpy as np
import ast
import re
import joblib
import pandas as pd
from datetime import datetime
from gen_cert.extract_metadata import extract_pdf_metadata

# Update model path
PKL_MODEL_PATH = r'f:\certificate-verification\models\metadata.pkl'

def is_valid_hash(blockchain_str):
    try:
        blockchain_dict = ast.literal_eval(blockchain_str)
        hash_val = blockchain_dict.get('hash', '')
        if not isinstance(hash_val, str) or not hash_val.startswith('0x'):
            return 0
        content = hash_val[2:]
        if len(content) != 32 or not re.fullmatch(r'[0-9a-fA-F]{32}', content) or set(content) == {'0'}:
            return 0
        return 1
    except:
        return 0

def validate_certificate(pdf_path):
    """Validate certificate using metadata model"""
    try:
        # Load metadata model
        metadata_model = joblib.load(PKL_MODEL_PATH)

        # Extract metadata and convert to DataFrame
        metadata = extract_pdf_metadata(pdf_path)
        
        # Print extracted metadata for verification
        print("\nExtracted Metadata:")
        for key, value in metadata.items():
            print(f"{key}: {value}")

        test_df = pd.DataFrame([metadata])

        # Convert dates to datetime
        test_df['issue_date'] = pd.to_datetime(test_df['issue_date'])
        test_df['expiry_date'] = pd.to_datetime(test_df['expiry_date'])

        # Feature engineering with debug prints
        print("\nCalculated Features:")
        print(f"Validity Days: {(test_df['expiry_date'] - test_df['issue_date']).dt.days.iloc[0]}")
        print(f"Hash Value: {test_df['blockchain'].iloc[0]}")
        
        # Feature engineering
        test_df['validity_days'] = (test_df['expiry_date'] - test_df['issue_date']).dt.days
        test_df['valid_hash'] = test_df['blockchain'].apply(is_valid_hash)
        test_df['is_expiry_missing'] = test_df['expiry_date'].isnull().astype(int)
        test_df['validity_days'] = test_df['validity_days'].fillna(-1)
        test_df['is_expiry_before_issue'] = (test_df['validity_days'] < 0).astype(int)
        test_df['hash_length'] = test_df['blockchain'].apply(
            lambda x: len(ast.literal_eval(x).get('hash', '')[2:]) if isinstance(ast.literal_eval(x), dict) else 0
        )
        test_df['days_since_issue'] = (pd.Timestamp.now() - test_df['issue_date']).dt.days
        test_df['suspicious_recipient'] = test_df['recipient_name'].isin(['Unknown', 'N/A', 'Test']).astype(int)
        test_df['suspicious_issuer'] = test_df['issuer_name'].isin(['Unknown', 'N/A', 'Test']).astype(int)

        # Basic validation features
        features = np.array([
            len(metadata['certificate_type']) > 0,
            len(metadata['recipient_name']) > 0,
            len(metadata['recipient_id']) > 0,
            len(metadata['issuer_name']) > 0,
            len(metadata['issuer_id']) > 0,
            not test_df['is_expiry_missing'].iloc[0],
            test_df['valid_hash'].iloc[0],
            test_df['hash_length'].iloc[0] >= 32,
            not test_df['suspicious_recipient'].iloc[0],
            not test_df['suspicious_issuer'].iloc[0],
            not test_df['is_expiry_before_issue'].iloc[0],
            test_df['validity_days'].iloc[0] > 0,
            test_df['days_since_issue'].iloc[0] >= 0
        ]).astype(float).reshape(1, -1)

        # Print feature values for debugging
        feature_names = [
            'Has Certificate Type',
            'Has Recipient Name',
            'Has Recipient ID',
            'Has Issuer Name',
            'Has Issuer ID',
            'Has Expiry Date',
            'Valid Hash Format',
            'Valid Hash Length',
            'Valid Recipient',
            'Valid Issuer',
            'Valid Date Order',
            'Valid Duration',
            'Valid Issue Date'
        ]
        
        print("\nFeature Values:")
        for name, value in zip(feature_names, features[0]):
            print(f"{name}: {'✓' if value == 1 else '✗'}")

        # Get metadata model prediction
        metadata_pred = metadata_model.predict(features)
        metadata_score = float(metadata_pred[0])
        
        print(f"\nRaw Model Score: {metadata_score}")
        # Print raw metadata for debugging
        print("\nRaw Metadata:")
        for key, value in metadata.items():
            print(f"{key}: {value}")

        return {
            'metadata_score': metadata_score,
            'is_valid': metadata_score >= 0.5,
            'details': {
                'valid_hash': bool(test_df['valid_hash'].iloc[0]),
                'suspicious_recipient': bool(test_df['suspicious_recipient'].iloc[0]),
                'suspicious_issuer': bool(test_df['suspicious_issuer'].iloc[0]),
                'valid_dates': not bool(test_df['is_expiry_before_issue'].iloc[0]),
                'validity_days': int(test_df['validity_days'].iloc[0])
            }
        }

    except Exception as e:
        return {'error': str(e)}

if __name__ == "__main__":
    pdf_path = r"gen_cert\certificates\John_Smith_20250413_143514.pdf"
    
    print("Validating Certificate Metadata...")
    result = validate_certificate(pdf_path)
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print("\nValidation Results:")
        print(f"Metadata Score: {result['metadata_score']:.2%}")
        print("\nDetailed Checks:")
        details = result['details']
        print(f"✓ Valid Hash: {'Yes' if details['valid_hash'] else 'No'}")
        print(f"✓ Valid Recipient: {'Yes' if not details['suspicious_recipient'] else 'No'}")
        print(f"✓ Valid Issuer: {'Yes' if not details['suspicious_issuer'] else 'No'}")
        print(f"✓ Valid Dates: {'Yes' if details['valid_dates'] else 'No'}")
        print(f"✓ Validity Period: {details['validity_days']} days")
        print(f"\nFinal Result: {'VALID' if result['is_valid'] else 'INVALID'}")