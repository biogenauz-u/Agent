"""Write a new encryption key to the ignored .env without printing it."""

import base64
import os
import secrets
from pathlib import Path

from dotenv import dotenv_values, set_key


def main() -> None:
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.is_file():
        raise SystemExit("Create .env from .env.example first.")
    if dotenv_values(path).get("DATA_ENCRYPTION_KEY"):
        raise SystemExit("DATA_ENCRYPTION_KEY already exists; refusing to replace it.")
    value = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    set_key(str(path), "DATA_ENCRYPTION_KEY", value, quote_mode="always")
    if os.name != "nt":
        path.chmod(0o600)
    print("Encryption key written to .env. Back it up securely; it was not printed.")


if __name__ == "__main__":
    main()
