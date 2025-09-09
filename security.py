# security.py

import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load the secret key from an environment variable
# This is crucial for security - the key is NOT in the code.
ENCRYPTION_KEY_STR = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY_STR:
    raise ValueError("No ENCRYPTION_KEY set for Flask application. Please set it in your .env file.")

# Convert the string key to bytes for the cryptography library
ENCRYPTION_KEY = ENCRYPTION_KEY_STR.encode()

# Initialize the Fernet cipher suite
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_token(token: str) -> bytes:
    """Encrypts a token string and returns it as bytes."""
    if not token:
        return None
    return cipher_suite.encrypt(token.encode('utf-8'))

def decrypt_token(encrypted_token: bytes) -> str:
    """Decrypts a token and returns it as a string."""
    if not encrypted_token:
        return None
    return cipher_suite.decrypt(encrypted_token).decode('utf-8')