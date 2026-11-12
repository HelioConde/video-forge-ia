"""Offline verification of the scheduled, non-generative health monitor."""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from scripts.check_videoforge_health import (
    WORKFLOWS, HealthCheckError, assess_runs, inspect_local_roster,
    main, make_report, write_summary,
)

NOW = datetime(2026, 11, 12, 20, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def run(*, status="completed", conclusion="success", minutes_old=4,
        event="push", branch="main", run_id=43200001001):
    return {
        "id": run_id,
        "head_branch": branch,
        "event": event,
        "created_at": (NOW-timedelta(minutes=minutes_old)).isoformat(),
        "status": status, "conclusion": conclusion,
        "name": "PRIVATE_DO_NOT_EXPOSE",
        "actor": {"login": "PRIVATE_DO_NOT_EXPOSE"},
    }


class ScheduledHealthTests(unittest.TestCase):
    def test_latest_push_main_is_only_relevant_run(self):
        items = [
            run(event="workflow_dispatch", conclusion="failure",
                minutes_old=1, run_id=43200001003),
            run(status="completed", conclusion="failure", branch="other",
                minutes_old=2, run_id=43200001002),
            run(status="completed", conclusion="success", minutes_old=3),
        ]
        result = assess_runs("validate.yml", items, now=NOW, required=True)
        self.assertEqual(result["state"], "success")
        self.assertFalse(result["problem"])
        self.assertEqual(result["run_id"], 43200001001)
        self.assertNotIn("PRIVATE_DO_NOT_EXPOSE", str(result))

    def test_failure_is_alert_but_never_retried(self):
        row = assess_runs("validate.yml", [run(conclusion="failure")], now=NOW,
                          required=True)
        self.assertTrue(row["problem"])
        self.assertEqual(row["state"], "failure")

    def test_running_not_declared_failed_until_stalled(self):
        row = assess_runs("pages.yml", [run(status="in_progress")], now=NOW,
                          required=True)
        self.assertEqual(row["state"], "running")
        self.assertFalse(row["problem"])
        stalled = assess_runs("pages.yml", [
            run(status="in_progress", minutes_old=91)], now=NOW, required=True)
        self.assertEqual(stalled["state"], "stalled")
        self.assertTrue(stalled["problem"])

    def test_latest_cancelled_is_not_invented_failure(self):
        row = assess_runs("validate.yml", [
            run(conclusion="cancelled")], now=NOW, required=True)
        self.assertEqual(row["state"], "cancelled")
        self.assertFalse(row["problem"])

    def test_missing_required_fails_but_optional_missing_does_not(self):
        self.assertTrue(assess_runs("validate.yml", [], now=NOW, required=True)["problem"])
        self.assertFalse(assess_runs("codex-proxy-backend.yml", [],
                                     now=NOW, required=False)["problem"])

    def test_local_roster_checks_actual_office_not_a_simulated_activity(self):
        info = inspect_local_roster()
        self.assertEqual(info["agents_registered"], 9)
        self.assertEqual(info["channels_registered"], 5)
        self.assertFalse(info["autonomous_execution_verified"])

    def test_report_queries_only_allowlisted_push_workflows(self):
        seen = []
        def fake_fetch(name, *, token):
            self.assertEqual(token, "SYNTHETIC_TEST_TOKEN")
            seen.append(name)
            return [run()]
        with (mock.patch("scripts.check_videoforge_health.fetch_runs",
                         side_effect=fake_fetch),
              mock.patch("scripts.check_videoforge_health.inspect_local_roster",
                         return_value={"agents_registered": 9, "channels_registered": 5})):
            report = make_report(token="SYNTHETIC_TEST_TOKEN", now=NOW)
        self.assertEqual(seen, [x[0] for x in WORKFLOWS])
        self.assertEqual(report["failures"], 0)
        self.assertEqual(report["proxy_calls"], 0)
        self.assertEqual(report["youtube_requests"], 0)
        self.assertEqual(report["videos_published"], 0)
        self.assertFalse(report["code_modified"])
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"summary.md"
            write_summary(report, p)
            output = p.read_text()
        self.assertIn("validate.yml", output)
        self.assertNotIn("PRIVATE_DO_NOT_EXPOSE", output)
        self.assertNotIn("SYNTHETIC_TEST_TOKEN", output)

    def test_runner_checks_repo_and_event_before_network(self):
        env = {
            "GITHUB_REPOSITORY": "attacker/other",
            "GITHUB_EVENT_NAME": "schedule",
            "GH_TOKEN": "secret",
        }
        with (mock.patch.dict(os.environ, env, clear=True),
              mock.patch("scripts.check_videoforge_health.fetch_runs",
                         side_effect=AssertionError("no network expected")),
              contextlib.redirect_stdout(io.StringIO()) as output):
            self.assertEqual(main(), 2)
        self.assertNotIn("secret", output.getvalue())

    def test_schedule_has_read_only_permissions_and_two_half_hour_checks(self):
        wf = (ROOT / ".github/workflows/videoforge-healthcheck.yml").read_text(
            encoding="utf-8")
        self.assertIn("cron: '12,42 * * * *'", wf)
        self.assertIn("actions: read", wf)
        self.assertIn("contents: read", wf)
        self.assertNotIn("contents: write", wf)
        self.assertNotIn("secrets.PROXY", wf)
        self.assertNotIn("secrets.YOUTUBE", wf)
        self.assertNotIn("secrets.PIXELLAB", wf)
        self.assertNotIn("workflow_dispatch: \n", wf)
        self.assertIn("test_health_monitor.py", wf)


if __name__ == "__main__":
    unittest.main()
