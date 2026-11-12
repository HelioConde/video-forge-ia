"""Editorial artifacts are encrypted, role-checked and bound to source run."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videoforge.channel_agents.secure_report import (
    EditorialReportCipherError, decrypt_editorial_report, encrypt_editorial_report,
)

ROOT = Path(__file__).resolve().parents[1]
CRYPTO_INSTALLED = importlib.util.find_spec("cryptography") is not None


def sample_report():
    return {
        "schema": "videoforge/editorial-team/v1",
        "channel": "otaku-br",
        "status": "awaiting_editorial_review_and_reservation",
        "chosen_topic": {"id": "pauta-1", "title": "PRIVATE_YOUTUBE_REPORT_TITLE"},
        "private_analytics": "PRIVATE_ANALYTICS_NEVER_PUBLIC",
        "proxy_calls": 1,
        "requires_human_editorial_review": True,
        "requires_topic_reservation": True,
        "images_generated": 0,
        "video_generated": False,
        "upload_enabled": False,
    }


@unittest.skipUnless(CRYPTO_INSTALLED, "cryptography is optional in offline CI")
class EditorialReportEncryptionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.key = base64.b64encode(os.urandom(32)).decode("ascii")
        self.source = self.dir / "private-decisions.json"
        self.encrypted = self.dir / "decisao.encrypted.json"
        self.restored = self.dir / "restored-private.json"
        self.source.write_text(json.dumps(sample_report()), encoding="utf-8")

    def test_authenticated_round_trip_no_plaintext_in_artifact(self):
        encrypt_editorial_report(self.source, key_b64=self.key,
                                 source_run_id="43200000001", output=self.encrypted)
        payload = self.encrypted.read_text(encoding="utf-8")
        self.assertNotIn("PRIVATE_YOUTUBE_REPORT_TITLE", payload)
        self.assertNotIn("PRIVATE_ANALYTICS_NEVER_PUBLIC", payload)
        self.assertNotIn("chosen_topic", payload)
        self.assertEqual(self.encrypted.stat().st_mode & 0o777, 0o600)
        decrypt_editorial_report(self.encrypted, key_b64=self.key,
                                 source_run_id="43200000001", output=self.restored)
        self.assertEqual(json.loads(self.restored.read_text()), sample_report())
        self.assertEqual(self.restored.stat().st_mode & 0o777, 0o600)

    def test_swap_run_wrong_key_and_tamper_never_create_plaintext(self):
        encrypt_editorial_report(self.source, key_b64=self.key,
                                 source_run_id="43200000001", output=self.encrypted)
        wrong_key = base64.b64encode(os.urandom(32)).decode("ascii")
        for run_id, key in (
            ("43200000002", self.key),
            ("43200000001", wrong_key),
        ):
            with self.subTest(run_id=run_id), self.assertRaisesRegex(
                    EditorialReportCipherError, "DECRYPT_FAILED"):
                decrypt_editorial_report(self.encrypted, key_b64=key,
                                         source_run_id=run_id, output=self.restored)
            self.assertFalse(self.restored.exists())
        payload = json.loads(self.encrypted.read_text())
        payload["nonce_b64"] = base64.b64encode(b"\x01"*12).decode("ascii")
        self.encrypted.write_text(json.dumps(payload))
        with self.assertRaisesRegex(EditorialReportCipherError, "DECRYPT_FAILED"):
            decrypt_editorial_report(self.encrypted, key_b64=self.key,
                                     source_run_id="43200000001", output=self.restored)
        self.assertFalse(self.restored.exists())

    def test_invalid_report_and_existing_path_fail_closed(self):
        bad = sample_report()
        bad["upload_enabled"] = True
        self.source.write_text(json.dumps(bad))
        with self.assertRaisesRegex(EditorialReportCipherError, "SCHEMA_INVALID"):
            encrypt_editorial_report(self.source, key_b64=self.key,
                                     source_run_id="43200000001", output=self.encrypted)
        self.assertFalse(self.encrypted.exists())
        self.source.write_text(json.dumps(sample_report()))
        self.encrypted.write_text("do-not-overwrite")
        with self.assertRaisesRegex(EditorialReportCipherError, "OUTPUT_ALREADY_EXISTS"):
            encrypt_editorial_report(self.source, key_b64=self.key,
                                     source_run_id="43200000001", output=self.encrypted)
        self.assertEqual(self.encrypted.read_text(), "do-not-overwrite")

    def test_cli_uses_local_key_only_and_no_generation(self):
        from videoforge.channel_agents.secure_report import main
        with mock.patch.dict(os.environ, {
                "VIDEOFORGE_DRAFT_ENCRYPTION_KEY_B64": self.key}):
            self.assertEqual(main(["encrypt", "--source", str(self.source),
                                   "--source-run-id", "43200000001",
                                   "--output", str(self.encrypted)]), 0)
            self.assertEqual(main(["decrypt", "--source", str(self.encrypted),
                                   "--source-run-id", "43200000001",
                                   "--output", str(self.restored)]), 0)
        self.assertEqual(json.loads(self.restored.read_text()), sample_report())


class EditorialWorkflowSecurityTests(unittest.TestCase):
    def test_model_research_only_owner_manual_dispatch(self):
        workflow = (ROOT / ".github/workflows/editorial-team-research.yml").read_text()
        self.assertIn("github.actor == 'HelioConde'", workflow)
        self.assertIn("inputs.authorize_research == true", workflow)
        self.assertIn("github.run_attempt == 1", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertNotIn("  push:\n", workflow)
        self.assertNotIn("head_commit.message", workflow)
        self.assertNotIn("test(editorial): one-shot authorized", workflow)

    def test_decision_artifact_is_encrypted_and_bound_to_same_run(self):
        source = (ROOT / ".github/workflows/editorial-team-research.yml").read_text()
        target = (ROOT / ".github/workflows/agent-one-briefing.yml").read_text()
        self.assertIn("secure_report encrypt", source)
        self.assertIn("secure_report decrypt", target)
        self.assertIn("decisao.encrypted.json", source)
        self.assertIn("decisao.encrypted.json", target)
        self.assertIn("otaku-multicena-agents-decisao-cifrada-", source)
        self.assertIn("otaku-multicena-agents-decisao-cifrada-", target)
        self.assertNotIn("path: output/editorial-team/decisao.json", source)
        self.assertIn("and record.get(\"event\") == \"workflow_dispatch\"", target)
        self.assertIn("and record.get(\"actor\", {}).get(\"login\") == \"HelioConde\"", target)


if __name__ == "__main__":
    unittest.main()
