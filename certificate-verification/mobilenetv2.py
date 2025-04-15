import requests

# MobileNet API configuration
API_BASE_URL = "https://06bf-35-243-202-36.ngrok-free.app"
file_path = "gen_cert/certificates/shiv_20250413_185807.pdf"

def predict_certificate(file_path):
    """Send certificate to MobileNet API for prediction"""
    try:
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(f"{API_BASE_URL}/predict", files=files)
            response.raise_for_status()
            result = response.json()
            return {
                'success': True,
                'prediction': result.get('prediction_score', 0),
                'is_valid': result.get('is_valid', False)
            }
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f"API connection error: {str(e)}"}
    except Exception as e:
        return {'success': False, 'error': f"Unexpected error: {str(e)}"}

if __name__ == "__main__":
    result = predict_certificate(file_path)
    if result['success']:
        print(f"AI Prediction Score: {result['prediction']:.2%}")
        print(f"Certificate Valid: {'Yes' if result['is_valid'] else 'No'}")
    else:
        print(f"Error: {result['error']}")
