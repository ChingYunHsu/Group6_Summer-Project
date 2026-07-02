"""Tier 2 application-level encryption for medical profile payloads.

This is layered on top of Tier 1 (MySQL tablespace encryption, see
db.verify_tablespace_encryption): even with disk/tablespace access, the
`encrypted_payload` column in `medical_profiles` is unreadable without the
application's Fernet key. The key is symmetric (AES-128-CBC + HMAC via
Fernet) and never touches the database — only ciphertext does.

Requires a `medical_profiles` table (not added here — schema/migrations are
owned elsewhere):

    CREATE TABLE medical_profiles (
      user_id VARCHAR(36) PRIMARY KEY,
      encrypted_payload LONGBLOB NOT NULL,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      CONSTRAINT fk_medical_profile_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
"""

import json

from cryptography.fernet import Fernet, InvalidToken

from settings import get_settings

_settings = get_settings()
_fernet = Fernet(_settings.medical_profile_encryption_key)


def encrypt_profile(data: dict) -> bytes:
    """Serialize and encrypt a medical profile payload for storage."""
    return _fernet.encrypt(json.dumps(data).encode("utf-8"))


def decrypt_profile(ciphertext: bytes) -> dict:
    """Decrypt and deserialize a stored medical profile payload.

    Raises cryptography.fernet.InvalidToken if the ciphertext is corrupt,
    tampered with, or was encrypted under a different key.
    """
    if isinstance(ciphertext, str):
        ciphertext = ciphertext.encode("utf-8")
    return json.loads(_fernet.decrypt(ciphertext).decode("utf-8"))


__all__ = ["encrypt_profile", "decrypt_profile", "InvalidToken"]
