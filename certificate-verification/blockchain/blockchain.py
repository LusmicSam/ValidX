from web3 import Web3
import json

# Connect to Ethereum node (using MetaMask for local interaction or Infura for testnet/mainnet)
# Example for local development
web3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

# Load your smart contract ABI and address
contract_address = "0xa7df1ba3e21f9ed6e2c4d1292e4ffb85ecc8fa5d"
abi = json.loads('abi.json')

# Set up your contract instance
contract = web3.eth.contract(address=contract_address, abi=abi)

# Set up your wallet from MetaMask
from_address = "0xf2C8BE73456C64e9FA5890f0E025E6A81B74fa45"
private_key = "e5ba7cf93ae12ef622a6344c3eebbdbd9c39b135445f0cbf44dc59f252db54b2"  # NEVER share your private key

def upload_hash_to_blockchain(ipfs_hash):
    """Upload the IPFS hash to the blockchain using the smart contract"""
    try:
        # Build the transaction
        transaction = contract.functions.addCertificate(ipfs_hash).buildTransaction({
            'chainId': 3,  # Ropsten testnet, change to 1 for mainnet
            'gas': 2000000,
            'gasPrice': web3.toWei('20', 'gwei'),
            'nonce': web3.eth.getTransactionCount(from_address),
        })

        # Sign the transaction
        signed_transaction = web3.eth.account.sign_transaction(transaction, private_key)

        # Send the transaction
        tx_hash = web3.eth.sendRawTransaction(signed_transaction.rawTransaction)

        # Wait for transaction receipt
        receipt = web3.eth.waitForTransactionReceipt(tx_hash)
        return receipt.transactionHash.hex()
    except Exception as e:
        print(f"Error uploading hash to blockchain: {e}")
        return None
