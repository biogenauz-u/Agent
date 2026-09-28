import asyncio
import hashlib
import os
import tempfile
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from pydantic import SecretStr

from app.core.encryption import CredentialEncryption
from app.modules.notebook.exceptions import (
    NotebookConfigurationError,
    NotebookIntegrityError,
    NotebookValidationError,
)


@dataclass(frozen=True)
class StoredFile:
    storage_name: str
    relative_path: str
    size: int
    checksum: str


class EncryptedLocalStorage:
    """Versioned AES-GCM local storage; paths never derive from user input."""

    def __init__(self, root: str | None, key: SecretStr | None, max_size_mb: int) -> None:
        if not root:
            raise NotebookConfigurationError("NOTEBOOK_STORAGE_PATH is required.")
        self.root = Path(root).expanduser().resolve()
        try:
            self.cipher = CredentialEncryption(key)
        except Exception as exc:
            raise NotebookConfigurationError("Valid DATA_ENCRYPTION_KEY is required.") from exc
        self.max_bytes = max_size_mb * 1024 * 1024

    async def initialize(self) -> None:
        await asyncio.to_thread(self.root.mkdir, parents=True, exist_ok=True)
        if not await self.health():
            raise NotebookConfigurationError("Notebook storage is not writable.")

    async def health(self) -> bool:
        def check() -> bool:
            try:
                self.root.mkdir(parents=True, exist_ok=True)
                fd, name = tempfile.mkstemp(prefix=".health-", dir=self.root)
                os.close(fd)
                Path(name).unlink(missing_ok=True)
                return True
            except OSError:
                return False

        return await asyncio.to_thread(check)

    def _target(self, owner: int, storage_name: str, year: int, month: int) -> tuple[Path, str]:
        relative = Path(str(owner)) / f"{year:04d}" / f"{month:02d}" / f"{storage_name}.enc"
        target = (self.root / relative).resolve()
        if self.root not in target.parents:
            raise NotebookIntegrityError("Invalid storage destination.")
        return target, relative.as_posix()

    async def save_bytes(self, owner: int, value: bytes, year: int, month: int) -> StoredFile:
        if len(value) > self.max_bytes:
            raise NotebookValidationError("Attachment exceeds configured size limit.")
        storage_name = uuid.uuid4().hex
        target, relative = self._target(owner, storage_name, year, month)
        checksum = hashlib.sha256(value).hexdigest()
        envelope = self.cipher.encrypt_bytes(value, owner, f"notebook_file:{storage_name}")

        def write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".upload-", dir=target.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(envelope)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)

        await asyncio.to_thread(write)
        return StoredFile(storage_name, relative, len(value), checksum)

    async def save_path(self, owner: int, source: Path, year: int, month: int) -> StoredFile:
        size = source.stat().st_size
        if size > self.max_bytes:
            raise NotebookValidationError("Attachment exceeds configured size limit.")
        value = await asyncio.to_thread(source.read_bytes)
        if len(value) != size:
            raise NotebookIntegrityError("Attachment changed during storage.")
        return await self.save_bytes(owner, value, year, month)

    async def read(self, owner: int, stored: StoredFile) -> bytes:
        target = (self.root / stored.relative_path).resolve()
        if self.root not in target.parents:
            raise NotebookIntegrityError("Invalid stored path.")
        try:
            envelope = await asyncio.to_thread(target.read_bytes)
            value = self.cipher.decrypt_bytes(
                envelope, owner, f"notebook_file:{stored.storage_name}"
            )
        except (OSError, Exception) as exc:
            if isinstance(exc, NotebookIntegrityError):
                raise
            raise NotebookIntegrityError("Attachment cannot be decrypted.") from exc
        if len(value) != stored.size or hashlib.sha256(value).hexdigest() != stored.checksum:
            raise NotebookIntegrityError("Attachment integrity check failed.")
        return value

    async def delete(self, relative_path: str) -> None:
        target = (self.root / relative_path).resolve()
        if self.root not in target.parents:
            raise NotebookIntegrityError("Invalid stored path.")
        await asyncio.to_thread(target.unlink, missing_ok=True)

    @asynccontextmanager
    async def decrypted_temp(self, owner: int, stored: StoredFile) -> AsyncIterator[Path]:
        value = await self.read(owner, stored)
        fd, name = tempfile.mkstemp(prefix="notebook-", suffix=".dec")
        path = Path(name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(value)
            yield path
        finally:
            await asyncio.to_thread(path.unlink, missing_ok=True)
