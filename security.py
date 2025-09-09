# security.py
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()
ENCRYPTION_KEY_STR = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY_STR:
    raise ValueError("ENCRYPTION_KEY is not set.")
ENCRYPTION_KEY = ENCRYPTION_KEY_STR.encode()
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_token_to_str(token: str) -> str:
    """Takes a string, encrypts it, and returns a URL-safe string."""
    if not token:
        return None
    encrypted_bytes = cipher_suite.encrypt(token.encode('utf-8'))
    return encrypted_bytes.decode('utf-8') # <-- CHANGE: return as string

def decrypt_token_from_str(encrypted_token_str: str) -> str:
    """Takes an encrypted string, decrypts it, and returns the original string."""
    if not encrypted_token_str:
        return None
    encrypted_bytes = encrypted_token_str.encode('utf-8') # <-- CHANGE: convert back to bytes
    decrypted_bytes = cipher_suite.decrypt(encrypted_bytes)
    return decrypted_bytes.decode('utf-8')