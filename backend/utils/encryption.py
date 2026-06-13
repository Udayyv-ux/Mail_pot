"""
Symmetric encryption for storing client SMTP passwords and API keys in the DB.
Uses Fernet (AES-128-CBC) derived from the JWT secret.
"""
import base64
import hashlib
from cryptography.fernet import Fernet
from backend.config import settings


def _get_fernet() -> Fernet:
    """Derive a Fernet key from JWT_SECRET."""
    key_bytes = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string and return base64-encoded ciphertext."""
    if not plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext back to plaintext."""
    if not ciphertext:
        return ""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
