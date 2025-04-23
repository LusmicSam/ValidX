import os
import requests
from flask import jsonify

# Pinata JWT configuration
JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySW5mb3JtYXRpb24iOnsiaWQiOiJiZmNiOTJjZC1lMjAxLTQxYjAtODdkMy02MGYyODRlOWY1OGMiLCJlbWFpbCI6InJzODM1MjQwNkBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwicGluX3BvbGljeSI6eyJyZWdpb25zIjpbeyJkZXNpcmVkUmVwbGljYXRpb25Db3VudCI6MSwiaWQiOiJGUkExIn0seyJkZXNpcmVkUmVwbGljYXRpb25Db3VudCI6MSwiaWQiOiJOWUMxIn1dLCJ2ZXJzaW9uIjoxfSwibWZhX2VuYWJsZWQiOmZhbHNlLCJzdGF0dXMiOiJBQ1RJVkUifSwiYXV0aGVudGljYXRpb25UeXBlIjoic2NvcGVkS2V5Iiwic2NvcGVkS2V5S2V5IjoiZDk4NDFiYjM1NjJhOTY3MDM2YTAiLCJzY29wZWRLZXlTZWNyZXQiOiI3YjQzZGNmYjM3NjgwOTE2NjE4NjkxOTZhZTg3NTYzMjkzYTVlOTJlNWFmNmExNGY1NTIzMzc0OTlmOTQxY2ZkIiwiZXhwIjoxNzc1Mjc5NDY3fQ.cYeHlyV0uw3HywbxiAc1JgUOkoD62TVp9QfPTePnUSk"

def upload_to_ipfs(file_path):
    """Upload a file to IPFS using Pinata API

    Args:
        file_path (str): Path to the file to upload

    Returns:
        dict: Response containing upload status and IPFS hash
    """
    try:
        # Pinata API endpoint
        url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
        
        # Request headers
        headers = {
            "Authorization": f"Bearer {JWT}"
        }

        # Prepare file for upload
        with open(file_path, "rb") as file:
            files = {
                "file": file
            }
            
            # Make the upload request
            response = requests.post(url, headers=headers, files=files)

        # Check if upload was successful
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "ipfs_hash": result["IpfsHash"],
                "name": result["PinataMetadata"]["name"],
                "size": result["PinataMetadata"]["keyvalues"]["size"] if "keyvalues" in result["PinataMetadata"] else None
            }
        else:
            return {
                "success": False,
                "error": f"Upload failed with status code: {response.status_code}"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }