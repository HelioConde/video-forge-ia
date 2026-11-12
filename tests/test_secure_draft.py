"""Crypto tests use only ephemeral test keys, not real accounts or tokens."""
import base64
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

from videoforge.production.secure_draft import (
    DraftCipherError, decrypt_private_draft, encrypt_private_draft,
)

CRYPTO_INSTALLED = importlib.util.find_spec("cryptography") is not None


@unittest.skipUnless(CRYPTO_INSTALLED, "cryptography dependency not installed")
class PrivateDraftCipherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = base64.b64encode(os.urandom(32)).decode("ascii")
        content = "Um briefing original para revisao independente"
        self.draft = {
            "schema": "videoforge/agent-task-draft/v1",
            "status": "awaiting_independent_review",
            "artifact_verified": False,
            "video_uploaded": False,
            "task_id": "briefing",
            "role_id": "coordenador-pautas",
            "provider": "codex_proxy",
            "content": content,
        }
        import hashlib
        self.draft["content_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.input_path = self.root / "draft.json"
        self.input_path.write_text(json.dumps(self.draft), encoding="utf-8")
        self.output_path = self.root / "draft.encrypted.json"

    def test_encrypt_is_authenticated_and_no_plaintext_leaks(self):
        summary = encrypt_private_draft(
            self.input_path, key_b64=self.key, source_run_id="43112345678",
            output_path=self.output_path
        )
        self.assertTrue(summary["encrypted"])
        self.assertFalse(summary["video_uploaded"])
        encoded = self.output_path.read_text(encoding="utf-8")
        self.assertNotIn("Um briefing original", encoded)
        self.assertNotIn("content", encoded)
        self.assertEqual(self.output_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(decrypt_private_draft(self.output_path, key_b64=self.key), self.draft)

    def test_wrong_key_and_tampering_rejected(self):
        encrypt_private_draft(
            self.input_path, key_b64=self.key, source_run_id="43112345678",
            output_path=self.output_path
        )
        wrong_key = base64.b64encode(os.urandom(32)).decode("ascii")
        with self.assertRaisesRegex(DraftCipherError, "DECRYPT_OR_FORMAT_FAILED"):
            decrypt_private_draft(self.output_path, key_b64=wrong_key)
        envelope = json.loads(self.output_path.read_text(encoding="utf-8"))
        envelope["source_run_id"] = "43112345679"
        self.output_path.write_text(json.dumps(envelope), encoding="utf-8")
        with self.assertRaisesRegex(DraftCipherError, "DECRYPT_OR_FORMAT_FAILED"):
            decrypt_private_draft(self.output_path, key_b64=self.key)

    def test_no_weak_key_plaintext_or_overwrite(self):
        with self.assertRaisesRegex(DraftCipherError, "KEY_INVALID"):
            encrypt_private_draft(
                self.input_path, key_b64="test-key", source_run_id="43112345678",
                output_path=self.output_path
            )
        self.draft["status"] = "approved"
        self.input_path.write_text(json.dumps(self.draft), encoding="utf-8")
        with self.assertRaisesRegex(DraftCipherError, "DRAFT_INVALID"):
            encrypt_private_draft(
                self.input_path, key_b64=self.key, source_run_id="43112345678",
                output_path=self.output_path
            )


if __name__ == "__main__":
    unittest.main()
