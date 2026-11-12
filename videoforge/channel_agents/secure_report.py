"""Protected handoff of editorial-agent decisions between GitHub Actions runs.

The research report can include non-public YouTube Analytics and model output;
GitHub Actions artifacts on a public repo must never contain its plaintext.
No network requests, generations, publications or retries occur here.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import secrets
from pathlib import Path

from videoforge.production.secure_draft import (
    DraftCipherError, _cipher, _key, _read,
)

RUN_ID = re.compile(r"^[0-9]{5,22}$")
REPORT_SCHEMA = "videoforge/editorial-team/v1"
ENVELOPE_SCHEMA = "videoforge/encrypted-editorial-report/v1"
DOMAIN = b"videoforge/editorial-report-aesgcm/v1:"


class EditorialReportCipherError(ValueError):
    """Fixed local error codes only, never plaintext or OAuth details."""


def _check_run_id(value: object) -> str:
    if not isinstance(value, str) or not RUN_ID.fullmatch(value):
        raise EditorialReportCipherError("EDITORIAL_REPORT_RUN_ID_INVALID")
    return value


def _validate_report(value: object) -> dict:
    if (not isinstance(value, dict)
            or value.get("schema") != REPORT_SCHEMA
            or value.get("channel") != "otaku-br"
            or value.get("status") != "awaiting_editorial_review_and_reservation"
            or not isinstance(value.get("chosen_topic"), dict)
            or value.get("proxy_calls") != 1
            or value.get("requires_human_editorial_review") is not True
            or value.get("requires_topic_reservation") is not True
            or value.get("images_generated") != 0
            or value.get("video_generated") is not False
            or value.get("upload_enabled") is not False):
        raise EditorialReportCipherError("EDITORIAL_REPORT_SCHEMA_INVALID")
    return value


def _sealed_path(path: Path, content: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise EditorialReportCipherError("EDITORIAL_REPORT_OUTPUT_ALREADY_EXISTS")
    if len(content) > 800_000:
        raise EditorialReportCipherError("EDITORIAL_REPORT_OUTPUT_TOO_LARGE")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        path.chmod(0o600)
    except OSError:
        path.unlink(missing_ok=True)
        raise EditorialReportCipherError("EDITORIAL_REPORT_WRITE_FAILED") from None


def encrypt_editorial_report(source: Path, *, key_b64: str,
                            source_run_id: str, output: Path) -> None:
    run_id = _check_run_id(source_run_id)
    try:
        raw = _read(source, maximum=600_000)
        _validate_report(json.loads(raw))
        nonce = secrets.token_bytes(12)
        encrypted = _cipher()(_key(key_b64)).encrypt(
            nonce, raw, DOMAIN + run_id.encode("ascii"))
    except EditorialReportCipherError:
        raise
    except (DraftCipherError, OSError, ValueError, TypeError, UnicodeError):
        raise EditorialReportCipherError("EDITORIAL_REPORT_ENCRYPT_FAILED") from None
    envelope = {
        "schema": ENVELOPE_SCHEMA,
        "algorithm": "AES-256-GCM",
        "source_run_id": run_id,
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "ciphertext_b64": base64.b64encode(encrypted).decode("ascii"),
    }
    _sealed_path(output, (json.dumps(envelope, sort_keys=True) + "\n").encode("utf-8"))


def decrypt_editorial_report(source: Path, *, key_b64: str,
                            source_run_id: str, output: Path) -> None:
    run_id = _check_run_id(source_run_id)
    try:
        env = json.loads(_read(source, maximum=800_000))
        if (not isinstance(env, dict)
                or env.get("schema") != ENVELOPE_SCHEMA
                or env.get("algorithm") != "AES-256-GCM"
                or env.get("source_run_id") != run_id):
            raise ValueError()
        nonce = base64.b64decode(env["nonce_b64"], validate=True)
        ciphertext = base64.b64decode(env["ciphertext_b64"], validate=True)
        if len(nonce) != 12 or len(ciphertext) > 650_000:
            raise ValueError()
        raw = _cipher()(_key(key_b64)).decrypt(
            nonce, ciphertext, DOMAIN + run_id.encode("ascii"))
        _validate_report(json.loads(raw))
    except (DraftCipherError, OSError, ValueError, TypeError,
            UnicodeError, KeyError, EditorialReportCipherError):
        raise EditorialReportCipherError("EDITORIAL_REPORT_DECRYPT_FAILED") from None
    except Exception as exc:
        if type(exc).__name__ == "InvalidTag":
            raise EditorialReportCipherError("EDITORIAL_REPORT_DECRYPT_FAILED") from None
        raise
    _sealed_path(output, raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Editorial report AES-GCM, no generation.")
    parser.add_argument("action", choices=("encrypt", "decrypt"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-run-id", required=True)
    args = parser.parse_args(argv)
    key = os.getenv("VIDEOFORGE_DRAFT_ENCRYPTION_KEY_B64", "")
    try:
        if args.action == "encrypt":
            encrypt_editorial_report(args.source, key_b64=key,
                                     source_run_id=args.source_run_id, output=args.output)
            print("EDITORIAL_REPORT_ENCRYPTED_NO_PLAINTEXT_ARTIFACT")
        else:
            decrypt_editorial_report(args.source, key_b64=key,
                                     source_run_id=args.source_run_id, output=args.output)
            print("EDITORIAL_REPORT_DECRYPTED_ON_PRIVATE_RUNNER")
        return 0
    except EditorialReportCipherError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
