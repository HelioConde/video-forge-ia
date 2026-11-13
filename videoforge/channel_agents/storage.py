"""Channel-scoped local artifacts. Never publish private analytics to Git.

Public research and reservation sources live in canal/<slug>/editorial/.
Runtime outputs live in ignored output/<slug>/... or a protected runner root.
A generated file for one channel must never be accepted in another's folder.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\\Z")


class ChannelStorageError(ValueError):
    """Safe, fixed-code path or channel identity failure."""


def channel_output_root(channel: str, *, root: Path = ROOT,
                        private_base: Path | None = None) -> Path:
    """Return the designated output directory for one registered channel.

    `root` is the repository root; `private_base` is an optional protected,
    temporary runner storage root (NOT a Git-tracked directory).
    """
    if not isinstance(channel, str) or len(channel) > 60 or not SLUG.fullmatch(channel):
        raise ChannelStorageError("CHANNEL_STORAGE_SLUG_INVALID")
    root = Path(root).resolve()
    folder = root / "canal" / channel
    config = folder / "canal.json"
    if folder.is_symlink() or config.is_symlink() or not config.is_file():
        raise ChannelStorageError("CHANNEL_STORAGE_CHANNEL_NOT_REGISTERED")
    try:
        parsed = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise ChannelStorageError("CHANNEL_STORAGE_CONFIG_INVALID") from None
    if not isinstance(parsed, dict) or parsed.get("id") != channel:
        raise ChannelStorageError("CHANNEL_STORAGE_CONFIG_MISMATCH")
    base = Path(private_base) if private_base is not None else root / "output"
    if base.is_symlink() or (base / channel).is_symlink():
        raise ChannelStorageError("CHANNEL_STORAGE_SYMLINK_NOT_ALLOWED")
    return base / channel


def channel_output_file(channel: str, destination: Path, *, root: Path = ROOT,
                        private_base: Path | None = None) -> Path:
    """Validate destination stays inside the correct channel's output tree."""
    target_root = channel_output_root(channel, root=root, private_base=private_base)
    target = Path(destination)
    if not target.is_absolute():
        target = Path(root) / target
    resolved_base = target_root.resolve()
    resolved = target.resolve()
    if resolved == resolved_base or not resolved.is_relative_to(resolved_base):
        raise ChannelStorageError("CHANNEL_STORAGE_CROSS_CHANNEL_PATH")
    # Do not permit symlinks, even ones that resolve back inside this channel.
    current = target_root
    for part in resolved.relative_to(resolved_base).parts:
        current = current / part
        if current.is_symlink():
            raise ChannelStorageError("CHANNEL_STORAGE_SYMLINK_NOT_ALLOWED")
    if target.is_symlink():
        raise ChannelStorageError("CHANNEL_STORAGE_SYMLINK_NOT_ALLOWED")
    return target
