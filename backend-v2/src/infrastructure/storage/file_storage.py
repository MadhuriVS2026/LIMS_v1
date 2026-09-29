"""
Local filesystem attachment storage.

Kept as its own adapter so `AttachmentService` never builds a path itself. That
separation is what makes the path-traversal guarantee checkable in one place:
every read and write goes through `_resolve`, which refuses anything that does
not land directly inside the configured root.

Swapping this for S3 or a document store later means implementing the same three
operations; the service holds no filesystem assumptions beyond "a stored name
maps to a readable path".
"""
from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

#  64KB reads: large enough to be efficient, small enough that an upload never
#  sits in memory in full.
CHUNK_SIZE = 64 * 1024

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


class StorageError(RuntimeError):
    """Raised when stored bytes cannot be written, located or removed."""


class LocalFileStorage:
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    # ── Naming ───────────────────────────────────────────────────────

    def build_storage_name(self, original_filename: str) -> str:
        """
        Build the on-disk name.

        The client's filename contributes only a sanitised extension, so someone
        looking at the directory can tell a PDF from a CSV. Uniqueness comes from
        a UTC timestamp plus 16 bytes of `secrets` entropy — never from the
        client — so two uploads of `chromatogram.pdf` cannot collide and a
        hostile name cannot steer the path.
        """
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        return f"{stamp}-{secrets.token_hex(16)}{safe_extension(original_filename)}"

    # ── Path resolution ──────────────────────────────────────────────

    def _resolve(self, storage_name: str) -> Path:
        """
        Map a storage name to a path inside the root, or refuse.

        Three checks, each catching something the others miss: a name carrying a
        separator or NUL, a name that is absolute or a dot-segment, and — after
        resolution — a path that escaped the root anyway through a symlink or a
        `..` that survived. This is the single choke point for path traversal.
        """
        if not storage_name:
            raise StorageError("Storage name is empty")
        if any(ch in storage_name for ch in ("/", "\\", "\0")):
            raise StorageError(f"Storage name must not contain a path separator: {storage_name!r}")
        if storage_name in (".", "..") or Path(storage_name).is_absolute():
            raise StorageError(f"Invalid storage name: {storage_name!r}")

        root = self._root.resolve()
        candidate = (root / storage_name).resolve()
        if candidate.parent != root:
            raise StorageError(f"Storage name escapes the storage root: {storage_name!r}")
        return candidate

    def path(self, storage_name: str) -> Path:
        """The resolved path for a stored name, whether or not it exists."""
        return self._resolve(storage_name)

    def exists(self, storage_name: str) -> bool:
        try:
            return self._resolve(storage_name).is_file()
        except StorageError:
            return False

    # ── Write ────────────────────────────────────────────────────────

    def open_writer(self, storage_name: str) -> "_StagedWrite":
        """
        Begin a staged write.

        Bytes go to a hidden `.part` sibling and are only renamed into place on
        `commit()`. A rejected or failed upload therefore never leaves a
        truncated file that would look like a complete attachment — which matters
        because the size cap is only discovered part-way through a large upload.
        """
        target = self._resolve(storage_name)
        return _StagedWrite(target)

    # ── Delete ───────────────────────────────────────────────────────

    def delete(self, storage_name: str) -> None:
        """Remove stored bytes. An absent file is not an error, so this is safe to retry."""
        try:
            self._resolve(storage_name).unlink(missing_ok=True)
        except StorageError:
            #  An unresolvable name has no bytes to remove. Raising here would
            #  leave a metadata row that could never be deleted.
            return
        except OSError as exc:
            raise StorageError(f"Could not delete attachment: {exc}") from exc


class _StagedWrite:
    """A write-in-progress that is only visible under its real name once committed."""

    def __init__(self, target: Path) -> None:
        self._target = target
        self._temp = target.with_name(f".{target.name}.part")
        self._handle = None

    def __enter__(self) -> "_StagedWrite":
        self._target.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._handle = open(self._temp, "wb")
        except OSError as exc:
            raise StorageError(f"Could not open attachment storage for writing: {exc}") from exc
        return self

    def write(self, chunk: bytes) -> None:
        try:
            self._handle.write(chunk)  # type: ignore[union-attr]
        except OSError as exc:
            raise StorageError(f"Could not write attachment bytes: {exc}") from exc

    def commit(self) -> None:
        try:
            self._handle.flush()  # type: ignore[union-attr]
            os.fsync(self._handle.fileno())  # type: ignore[union-attr]
            self._handle.close()  # type: ignore[union-attr]
            self._handle = None
            os.replace(self._temp, self._target)
        except OSError as exc:
            raise StorageError(f"Could not finalise attachment: {exc}") from exc

    def __exit__(self, exc_type, exc, tb) -> None:
        #  Whatever happened, the staging file must not survive. If commit() ran
        #  it is already gone; otherwise this is the cleanup that keeps a
        #  rejected upload from leaving anything behind.
        if self._handle is not None:
            try:
                self._handle.close()
            except OSError:
                pass
            self._handle = None
        self._temp.unlink(missing_ok=True)


def safe_extension(original_filename: str) -> str:
    """
    The sanitised final extension of a client filename, or `''`.

    `../../etc/passwd` yields `''` and `report.tar.gz` yields `.gz`. Losing
    `.tar` is fine: the stored name is never what a user downloads as — the
    original filename is sent back as the download name.
    """
    suffix = Path(original_filename or "").suffix
    cleaned = _UNSAFE.sub("", suffix)
    return cleaned[:20] if cleaned.startswith(".") and len(cleaned) > 1 else ""
