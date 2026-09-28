import base64
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.modules.notebook.exceptions import (
    NotebookIntegrityError,
    NotebookValidationError,
)
from app.modules.notebook.storage import EncryptedLocalStorage
from app.modules.notebook.utils import safe_original_name, validate_url


def key() -> SecretStr:
    return SecretStr(base64.urlsafe_b64encode(b"n" * 32).decode())


async def test_encrypted_storage_round_trip_and_plaintext_absent(tmp_path: Path) -> None:
    storage = EncryptedLocalStorage(str(tmp_path), key(), 1)
    await storage.initialize()
    stored = await storage.save_bytes(42, b"private notebook file", 2026, 9)
    raw = (tmp_path / stored.relative_path).read_bytes()
    assert b"private notebook file" not in raw
    assert await storage.read(42, stored) == b"private notebook file"
    assert stored.checksum == "4a770c95bb485d96dc8b7d705188bb1e63714ae0ec8bf173fd61e40cba608b34"


async def test_fresh_nonce_produces_different_envelopes(tmp_path: Path) -> None:
    storage = EncryptedLocalStorage(str(tmp_path), key(), 1)
    first = await storage.save_bytes(42, b"same", 2026, 9)
    second = await storage.save_bytes(42, b"same", 2026, 9)
    assert (tmp_path / first.relative_path).read_bytes() != (
        tmp_path / second.relative_path
    ).read_bytes()
    assert first.storage_name != second.storage_name


async def test_size_limit_is_enforced_before_storage(tmp_path: Path) -> None:
    storage = EncryptedLocalStorage(str(tmp_path), key(), 1)
    with pytest.raises(NotebookValidationError, match="size limit"):
        await storage.save_bytes(42, b"x" * (1024 * 1024 + 1), 2026, 9)
    assert not list(tmp_path.rglob("*.enc"))


async def test_tampering_fails_integrity(tmp_path: Path) -> None:
    storage = EncryptedLocalStorage(str(tmp_path), key(), 1)
    stored = await storage.save_bytes(42, b"secret", 2026, 9)
    target = tmp_path / stored.relative_path
    target.write_bytes(target.read_bytes()[:-1] + b"x")
    with pytest.raises(NotebookIntegrityError):
        await storage.read(42, stored)


async def test_decrypted_temp_is_removed(tmp_path: Path) -> None:
    storage = EncryptedLocalStorage(str(tmp_path), key(), 1)
    stored = await storage.save_bytes(42, b"temporary", 2026, 9)
    async with storage.decrypted_temp(42, stored) as path:
        assert path.read_bytes() == b"temporary"
        temporary = path
    assert not temporary.exists()


@pytest.mark.parametrize(
    ("unsafe", "safe"),
    [("../../secret.pdf", "secret.pdf"), (r"C:\private\book.xlsx", "book.xlsx")],
)
def test_original_filename_never_controls_path(unsafe: str, safe: str) -> None:
    assert safe_original_name(unsafe) == safe


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///etc/passwd", "data:x"])
def test_unsafe_link_schemes_rejected(url: str) -> None:
    with pytest.raises(NotebookValidationError):
        validate_url(url, ("http", "https"))


def test_http_links_validate_without_fetching() -> None:
    assert validate_url("https://example.com/a?q=1", ("http", "https")) == (
        "https://example.com/a?q=1"
    )
