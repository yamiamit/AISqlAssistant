"""
Symmetric encryption for target-database passwords stored in the app DB.

We use Fernet (AES-128-CBC + HMAC, from the `cryptography` package) rather
than storing raw plaintext. This is app-level encryption-at-rest for a
secret we must be able to decrypt again (to open a connection) — different
from password hashing (one-way, used for user login credentials).
"""
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_fernet = Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_value(plain_text: str) -> str:
    return _fernet.encrypt(plain_text.encode()).decode()


def decrypt_value(encrypted_text: str) -> str:
    try:
        return _fernet.decrypt(encrypted_text.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Stored credential could not be decrypted.") from exc
