"""No-generation checks for the first agent-led Otaku video."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from videoforge.production.otaku_video_readiness import (
    ROOT, SAMPLE, ReadinessError, _manifest_path, assess, main,
)


class FirstOtakuVideoTests(TestCase):
    def test_existing_sample_is_not_agent_produced_and_budget_is_insufficient(self):
        report = assess()
        self.assertEqual(report["channel"], "otaku-br")
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["can_render_now"])
        self.assertEqual(report["candidate_manifest"], "sample")
        self.assertTrue(report["manifest_structurally_valid"])
        self.assertEqual(report["target_duration_seconds"], 90)
        self.assertEqual(report["planned_image_requests"], 26)
        self.assertEqual(report["explicit_image_call_limit"], 12)
        self.assertEqual(report["budget_shortfall"], 14)
        self.assertEqual(report["reservation_claims_found"], 0)
        for expected in (
            "NO_HUMAN_APPROVED_EDITORIAL_RESERVATION",
            "NO_AUTHENTICATED_AGENT_DECISION_HANDOFF",
            "SAMPLE_STORY_NOT_SELECTED_BY_TEAM",
            "AGENT_SCRIPT_AND_STORYBOARD_PROVENANCE_NOT_VERIFIED",
            "IMAGE_CALL_BUDGET_BELOW_PLAN",
            "PROXY_TEXT_AND_IMAGE_QUOTA_NOT_VERIFIED",
            "HUMAN_RENDER_APPROVAL_NOT_RECORDED",
        ):
            self.assertIn(expected, report["blockers"])
        self.assertEqual(report["proxy_calls"], 0)
        self.assertEqual(report["images_generated"], 0)
        self.assertEqual(report["videos_uploaded"], 0)

    def test_budget_is_never_auto_raised_and_does_not_authorize_payment(self):
        report = assess(max_image_calls=26)
        self.assertNotIn("IMAGE_CALL_BUDGET_BELOW_PLAN", report["blockers"])
        self.assertFalse(report["can_render_now"])
        self.assertFalse(report["human_render_approved"])
        self.assertFalse(report["quota_verified"])
        with self.assertRaisesRegex(ReadinessError, "CALL_LIMIT_INVALID"):
            assess(max_image_calls=49)
        with self.assertRaisesRegex(ReadinessError, "CALL_LIMIT_INVALID"):
            assess(max_image_calls=True)

    def test_reservation_claim_alone_never_authenticates_agents(self):
        with mock.patch("videoforge.production.otaku_video_readiness._ledger",
                        return_value=[{"status": "approved_reserved",
                                       "human_approved": True,
                                       "source_run_id": "12345678"}]):
            report = assess(max_image_calls=26)
        self.assertEqual(report["reservation_claims_found"], 1)
        self.assertNotIn("NO_HUMAN_APPROVED_EDITORIAL_RESERVATION", report["blockers"])
        self.assertIn("NO_AUTHENTICATED_AGENT_DECISION_HANDOFF", report["blockers"])
        self.assertFalse(report["private_source_verified"])
        self.assertFalse(report["can_render_now"])

    def test_untrusted_paths_cannot_read_repo_secrets_or_other_channels(self):
        for value in (
            "../secrets.json", "/etc/passwd", "canal/gamer/videos/manifest.json",
            "AGENTS.md", ".github/workflows/autoeditor-generator.yml",
        ):
            with self.subTest(value=value), self.assertRaisesRegex(
                    ReadinessError, "MANIFEST_PATH"):
                _manifest_path(value, root=ROOT)

    def test_missing_video_manifest_is_reported_not_forged(self):
        with TemporaryDirectory() as temp:
            sandbox = Path(temp)
            for filename in (
                "canal/otaku-br/editorial/reservas.json",
                "geradores/autoeditor/gerador.json",
                "agentes/equipe.json",
            ):
                dest = sandbox / filename
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / filename, dest)
            result = assess(root=sandbox,
                            manifest_path="canal/otaku-br/videos/primeiro/manifest.json")
        self.assertEqual(result["candidate_manifest"], "missing")
        self.assertFalse(result["manifest_structurally_valid"])
        self.assertIsNone(result["planned_image_requests"])
        self.assertIn("NO_90_SECOND_RENDER_MANIFEST", result["blockers"])

    def test_cli_writes_blocked_report_without_network_or_generation(self):
        with TemporaryDirectory() as temp:
            report_path = Path(temp) / "otaku-ready.json"
            with mock.patch("videoforge.proxy.client.ProxyClient",
                            side_effect=AssertionError("No Proxy allowed")):
                result = main(["--output", str(report_path)])
            self.assertEqual(result, 0)
            data = json.loads(report_path.read_text())
            self.assertEqual(data["videos_rendered"], 0)
            self.assertFalse(data["can_render_now"])
            self.assertEqual(main(["--output", str(report_path)]), 1)

    def test_readiness_workflow_is_free_and_never_reports_video_generation(self):
        workflow = (ROOT / ".github/workflows/otaku-team-video-readiness.yml"
                    ).read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("test_otaku_video_readiness.py", workflow)
        self.assertIn("otaku_video_readiness", workflow)
        self.assertIn("contents: read", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("proxy-runtime", workflow)
        self.assertNotIn("youtube-analytics-readonly", workflow)
        self.assertNotIn("autoeditor --action produce", workflow)
        self.assertNotIn("secrets.PROXY_API_KEY", workflow)
        self.assertNotIn("actions/upload-artifact", workflow)


if __name__ == "__main__":
    import unittest
    unittest.main()
