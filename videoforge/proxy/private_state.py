"""Restauracao SOMENTE explicita de contas OAuth em runner privado efemero.

Nunca copiar contas do AutoEditorVideo automaticamente. Nunca exportar para
GitHub Pages, logs ou artifacts. A origem e um GitHub Environment Secret do
repositorio VideoForge AI configurado pelo proprietario.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

MAX_SECRET_BYTES = 45 * 1024


class PrivateStateError(ValueError):
    pass


def validate_private_state(raw: str) -> int:
    if not raw:
        raise PrivateStateError("MISSING_PRIVATE_STATE")
    if len(raw.encode("utf-8")) > MAX_SECRET_BYTES:
        raise PrivateStateError("PRIVATE_STATE_TOO_LARGE")
    try:
        data = json.loads(raw)
    except ValueError:
        raise PrivateStateError("PRIVATE_STATE_INVALID_JSON") from None
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise PrivateStateError("PRIVATE_STATE_INVALID_SCHEMA")
    records = data["records"]
    if not 1 <= len(records) <= 20:
        raise PrivateStateError("PRIVATE_STATE_INVALID_RECORD_COUNT")
    for row in records:
        if not isinstance(row, dict) or not isinstance(row.get("token"), dict):
            raise PrivateStateError("PRIVATE_STATE_INVALID_RECORD")
        if not all(isinstance(row["token"].get(k), str) and row["token"][k]
                   for k in ("access_token", "refresh_token")):
            raise PrivateStateError("PRIVATE_STATE_MISSING_OAUTH_FIELDS")
    return len(records)


def stage_private_state(raw: str, directory: Path) -> int:
    count = validate_private_state(raw)
    if directory.is_symlink() or directory.exists():
        raise PrivateStateError("PRIVATE_DIRECTORY_MUST_NOT_EXIST")
    directory.mkdir(parents=True, mode=0o700)
    directory.chmod(0o700)
    path = directory / "accounts.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(raw)
        path.chmod(0o600)
    except OSError:
        path.unlink(missing_ok=True)
        raise PrivateStateError("PRIVATE_STATE_STAGING_FAILED") from None
    return count
