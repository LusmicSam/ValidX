import requests
import os

# Pinata API credentials
API_KEY = "d9841bb3562a967036a0"
API_SECRET = "7b43dcfb3768091661869196ae87563293a5e92e5af6a14f552337499f941cfd"

def retrieve_from_pinata(filepath):
    """Upload a file to Pinata IPFS service

    Args:
        filepath (str): Path to the file to upload

    Returns:
        dict: Response containing upload status and IPFS hash
    """
    try:
        url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
        headers = {
            'pinata_api_key': API_KEY,
            'pinata_secret_api_key': API_SECRET
        }

        if not os.path.exists(filepath):
            return {
                "success": False,
                "error": "File not found"
            }

        with open(filepath, 'rb') as file:
            files = {'file': file}
            response = requests.post(url, files=files, headers=headers)

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "ipfs_hash": result.get("IpfsHash")
                }
            else:
                error_msg = response.json().get("error", {}).get("details") if response.json() else f"Upload failed with status code: {response.status_code}"
                return {
                    "success": False,
                    "error": error_msg
                }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Network error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
    