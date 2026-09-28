"""Versioned AES-256-GCM envelopes bound to the credential owner/provider."""

import base64
import binascii
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

from app.modules.calendar.exceptions import CalendarConfigurationError


class CredentialEncryption:
    def __init__(self, key: SecretStr | None) -> None:
        try:
            raw = (
                base64.b64decode(key.get_secret_value(), altchars=b"-_", validate=True)
                if key
                else b""
            )
            if len(raw) != 32:
                raise ValueError
        except (ValueError, binascii.Error):
            raise CalendarConfigurationError(
                "DATA_ENCRYPTION_KEY must be a Base64-encoded 32-byte key."
            ) from None
        self._cipher = AESGCM(raw)

    def encrypt(self, value: str, owner: int, purpose: str = "google_calendar") -> bytes:
        return self.encrypt_bytes(value.encode(), owner, purpose)

    def encrypt_bytes(self, value: bytes, owner: int, purpose: str) -> bytes:
        nonce = secrets.token_bytes(12)
        return (
            b"\x01"
            + nonce
            + self._cipher.encrypt(nonce, value, f"{purpose}:{owner}:v1".encode())
        )

    def decrypt(self, value: bytes, owner: int, purpose: str = "google_calendar") -> str:
        try:
            return self.decrypt_bytes(value, owner, purpose).decode()
        except UnicodeError:
            raise CalendarConfigurationError(
                "Stored encrypted value cannot be decoded."
            ) from None

    def decrypt_bytes(self, value: bytes, owner: int, purpose: str) -> bytes:
        try:
            if value[:1] != b"\x01":
                raise ValueError
            return self._cipher.decrypt(
                value[1:13], value[13:], f"{purpose}:{owner}:v1".encode()
            )
        except (InvalidTag, ValueError):
            raise CalendarConfigurationError(
                "Stored encrypted value cannot be decrypted."
            ) from None
