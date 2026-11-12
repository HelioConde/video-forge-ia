"""Encrypt private agent drafts before storing GitHub Actions artifacts.

Requires optional cryptography dependency at execution time. Public artifacts
contain only nonce, ciphertext and non-sensitive envelope metadata.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
from pathlib import Path


class DraftCipherError(ValueError):
    """Never include provider text or decrypted secret material in errors."""


def _cipher():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise DraftCipherError("DRAFT_CIPHER_DEPENDENCY_MISSING") from None
    return AESGCM


def _key(raw: str | None) -> bytes:
    try:
        result = base64.b64decode(raw or "", validate=True)
    except (ValueError, TypeError):
        raise DraftCipherError("DRAFT_CIPHER_KEY_INVALID") from None
    if len(result) != 32:
        raise DraftCipherError("DRAFT_CIPHER_KEY_INVALID")
    return result


def _read(path: Path, *, maximum: int = 128000) -> bytes:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise DraftCipherError("DRAFT_CIPHER_INPUT_UNSAFE")
    return path.read_bytes()


def encrypt_private_draft(draft_path: Path, *, key_b64: str,
                          source_run_id: str, output_path: Path) -> dict:
    if not isinstance(source_run_id, str) or not (source_run_id.isascii()
            and source_run_id.isdecimal() and 5 <= len(source_run_id) <= 22):
        raise DraftCipherError("DRAFT_CIPHER_RUN_ID_INVALID")
    raw = _read(draft_path)
    try:
        draft = json.loads(raw)
        if (not isinstance(draft, dict)
                or draft.get("schema") != "videoforge/agent-task-draft/v1"
                or draft.get("status") != "awaiting_independent_review"
                or draft.get("artifact_verified") is not False
                or draft.get("video_uploaded") is not False
                or draft.get("task_id") != "briefing"
                or draft.get("provider") != "codex_proxy"
                or draft.get("role_id") != "coordenador-pautas"
                or not isinstance(draft.get("content"), str)
                or not draft["content"]
                or draft.get("content_sha256") != hashlib.sha256(
                    draft["content"].encode("utf-8")
                ).hexdigest()):
            raise ValueError()
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise DraftCipherError("DRAFT_CIPHER_DRAFT_INVALID") from None
    key = _key(key_b64)
    if output_path.exists() or output_path.is_symlink():
        raise DraftCipherError("DRAFT_CIPHER_OUTPUT_EXISTS")
    aad = ("videoforge/draft-aesgcm/v1:" + source_run_id).encode("ascii")
    nonce = secrets.token_bytes(12)
    ciphertext = _cipher()(key).encrypt(nonce, raw, aad)
    envelope = {
        "schema": "videoforge/encrypted-agent-draft/v1",
        "algorithm": "AES-256-GCM",
        "source_run_id": source_run_id,
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # No secret or plaintext on stdout/Actions Summary.
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    with os.fdopen(os.open(output_path, flags, 0o600), "w", encoding="utf-8") as stream:
        json.dump(envelope, stream, ensure_ascii=True, indent=2)
        stream.write("\n")
    return {"encrypted": True, "status": "awaiting_independent_review",
            "video_uploaded": False, "source_run_id": source_run_id}


def decrypt_private_draft(envelope_path: Path, *, key_b64: str) -> dict:
    """Local review helper: caller must protect result, never log or publish it."""
    try:
        envelope = json.loads(_read(envelope_path, maximum=200000))
        if (envelope.get("schema") != "videoforge/encrypted-agent-draft/v1"
                or envelope.get("algorithm") != "AES-256-GCM"):
            raise ValueError()
        run_id = envelope["source_run_id"]
        if not isinstance(run_id, str) or not run_id.isascii() or not run_id.isdecimal():
            raise ValueError()
        nonce = base64.b64decode(envelope["nonce_b64"], validate=True)
        data = base64.b64decode(envelope["ciphertext_b64"], validate=True)
        if len(nonce) != 12:
            raise ValueError()
        aad = ("videoforge/draft-aesgcm/v1:" + run_id).encode("ascii")
        plaintext = _cipher()(_key(key_b64)).decrypt(nonce, data, aad)
        draft = json.loads(plaintext)
        if draft.get("schema") != "videoforge/agent-task-draft/v1":
            raise ValueError()
        return draft
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise DraftCipherError("DRAFT_CIPHER_DECRYPT_OR_FORMAT_FAILED") from None
    except Exception as exc:
        if type(exc).__name__ == "InvalidTag":
            raise DraftCipherError("DRAFT_CIPHER_DECRYPT_OR_FORMAT_FAILED") from None
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Encrypt protected draft. No plaintext output.")
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-run-id", required=True)
    args = parser.parse_args()
    key = os.getenv("VIDEOFORGE_DRAFT_ENCRYPTION_KEY_B64")
    encrypt_private_draft(args.draft, key_b64=key or "",
                          source_run_id=args.source_run_id,
                          output_path=args.output)
    print("DRAFT_ENCRYPTED_AWAITING_INDEPENDENT_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
