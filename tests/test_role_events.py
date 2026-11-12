"""Role-check telemetry must never claim a job without real output."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from videoforge.production.role_events import (
    CheckReporter, StageEvidenceError, role_task, valid_context,
)


class RoleEventTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "VF_CHECK_TOKEN": "dummy-mocked-token",
            "GITHUB_REPOSITORY": "HelioConde/video-forge-ia",
            "GITHUB_SHA": "a" * 40,
            "GITHUB_RUN_ID": "43147397260",
        }

        self.status_events = []
        def mocked_status(context, payload):
            self.status_events.append(payload)
            return {"id": len(self.status_events)}
        status_patch = patch("videoforge.production.role_events._status_request",
                             side_effect=mocked_status)
        status_patch.start()
        self.addCleanup(status_patch.stop)

    def test_no_token_stays_unconnected_and_requires_actual_evidence(self):
        self.assertIsNone(valid_context({}))
        reporter = CheckReporter(env={}, channel="otaku-br")
        with tempfile.TemporaryDirectory() as d:
            proof = Path(d) / "real.wav"
            with self.assertRaisesRegex(StageEvidenceError, "EVIDENCE_MISSING"):
                with role_task("narrador", evidence=(proof,), reporter=reporter):
                    pass
            with role_task("narrador", evidence=(proof,), reporter=reporter):
                proof.write_bytes(b"real-output")
            self.assertEqual(reporter.checks, {})

    def test_roles_are_created_after_start_and_closed_after_real_output(self):
        events = []
        def fake(context, method, endpoint, body):
            events.append((method, endpoint, body))
            return {"id": 123} if method == "POST" else {}
        reporter = CheckReporter(self.env, channel="otaku-br")
        with patch("videoforge.production.role_events._request", side_effect=fake):
            with tempfile.TemporaryDirectory() as d:
                proof = Path(d) / "voice.wav"
                with role_task("narrador", evidence=(proof,), reporter=reporter):
                    self.assertEqual(len(events), 1)
                    self.assertEqual(events[0][2]["status"], "in_progress")
                    proof.write_bytes(b"real")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1][2]["conclusion"], "success")
        self.assertEqual(events[0][2]["external_id"],
                         "vf-autoeditor:43147397260:otaku-br:narrador")
        self.assertNotIn("dummy-mocked-token", repr(events))

    def test_failure_results_in_failed_check_never_success(self):
        events = []
        def fake(context, method, endpoint, body):
            events.append((method, endpoint, body))
            return {"id": 124} if method == "POST" else {}
        reporter = CheckReporter(self.env, channel="otaku-br")
        with patch("videoforge.production.role_events._request", side_effect=fake):
            with self.assertRaisesRegex(RuntimeError, "PRODUCER_FAILURE"):
                with role_task("artista", reporter=reporter):
                    raise RuntimeError("PRODUCER_FAILURE")
        self.assertEqual(events[-1][2]["conclusion"], "failure")
        self.assertNotIn("PRODUCER_FAILURE", repr(events))

    def test_no_unsafe_context_and_no_unregistered_roles(self):
        bad = dict(self.env, GITHUB_REPOSITORY="Somebody/OtherRepo")
        self.assertIsNone(valid_context(bad))
        with self.assertRaisesRegex(StageEvidenceError, "UNKNOWN_ROLE"):
            with role_task("publicador", reporter=CheckReporter(env={}, channel="otaku-br")):
                pass
        reporter = CheckReporter(self.env, channel="../private")
        with patch("videoforge.production.role_events._request") as handler:
            reporter.start("narrador")
            handler.assert_not_called()

    def test_commit_status_tracks_actual_stages_without_private_details(self):
        reporter = CheckReporter(self.env, channel="otaku-br")
        with patch("videoforge.production.role_events._request",
                   side_effect=ValueError("checks API unavailable")):
            with tempfile.TemporaryDirectory() as d:
                evidence = Path(d) / "video.mp4"
                with role_task("editor", evidence=(evidence,), reporter=reporter):
                    self.assertEqual(self.status_events[-1]["state"], "pending")
                    evidence.write_bytes(b"verified render")
        self.assertEqual([x["state"] for x in self.status_events],
                         ["pending", "success"])
        self.assertEqual(self.status_events[-1]["context"],
                         "VideoForge Stage / autoeditor / otaku-br / editor")
        self.assertEqual(self.status_events[-1]["target_url"],
                         "https://github.com/HelioConde/video-forge-ia/actions/runs/43147397260")
        self.assertNotIn("dummy-mocked-token", repr(self.status_events))
        self.assertFalse(reporter.checks)

    def test_commit_status_reports_failure_after_real_stage_failure(self):
        reporter = CheckReporter(self.env, channel="otaku-br")
        with patch("videoforge.production.role_events._request", return_value={"id": 21}):
            with self.assertRaisesRegex(ValueError, "render failed"):
                with role_task("editor", reporter=reporter):
                    raise ValueError("render failed")
        self.assertEqual([x["state"] for x in self.status_events],
                         ["pending", "failure"])

    def test_telemetry_http_failure_never_exposes_credentials(self):
        reporter = CheckReporter(self.env, channel="otaku-br")
        with patch("videoforge.production.role_events._request",
                   side_effect=ValueError("secret sent by upstream")):
            reporter.start("editor")
        self.assertEqual(reporter.checks, {})


if __name__ == "__main__":
    unittest.main()
