"""Quota diagnostics are read-only and omit all identifying fields."""
from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
import os
from unittest import TestCase, mock

from videoforge.proxy.client import ProxyError
from videoforge.proxy.quota_diagnostic import summarize_quota

NOW = datetime(2026, 11, 12, 18, 0, tzinfo=timezone.utc)


class FakeQuotaProxy:
    def __init__(self, *, eligible=True, quota=None, error=None):
        self.eligible = eligible
        self.quota = quota
        self.error = error
        self.calls = []
    def accounts(self):
        return {"accounts": [{
            "id": "NEVER_PUBLIC_ACCOUNT_ID",
            "email": "NEVER_PUBLIC_EMAIL",
            "last_error": "NEVER_PUBLIC_PROVIDER_ERROR",
            "plan_type": "NEVER_PUBLIC_PLAN",
            "eligible_now": self.eligible,
            "status": "active",
            "cached_quota": self.quota,
            "cooldown_until": None,
        }]}
    def account_usage(self, account_id, *, cached=True):
        self.calls.append((account_id, cached))
        if self.error:
            raise ProxyError(self.error)
        return {"quota_runtime": self.quota,
                "email": "NEVER_PUBLIC_EMAIL",
                "credits": {"balance": 9999}}


def quota(*, primary=False, secondary=False, timestamp=NOW):
    return {
        "rate_limit": {"allowed": True, "limit_reached": primary,
                       "used_percent": 100 if primary else 10},
        "secondary_rate_limit": {"allowed": True, "limit_reached": secondary},
        "credits": {"balance": 900, "active_limit": "private"},
        "fetched_at": timestamp.isoformat(),
    }


class QuotaTests(TestCase):
    def test_cached_limit_is_bounded_and_never_outputs_id_or_credits(self):
        proxy = FakeQuotaProxy(quota=quota(primary=True))
        report = summarize_quota(proxy, now=NOW)
        self.assertEqual(proxy.calls, [])
        self.assertEqual(report["status"], "restriction_reported")
        self.assertEqual(report["primary_window"], "limit_reported")
        self.assertEqual(report["quota_age_bucket"], "within_15_minutes")
        self.assertEqual(report["read_only_usage_requests"], 0)
        self.assertFalse(report["429_cause_proven"])
        output = json.dumps(report)
        for secret in ("NEVER_PUBLIC", "balance", "used_percent", "active_limit"):
            self.assertNotIn(secret, output)

    def test_cached_missing_cannot_promise_a_successful_generation(self):
        proxy = FakeQuotaProxy(quota=None)
        report = summarize_quota(proxy, now=NOW)
        self.assertEqual(report["status"], "quota_not_observed")
        self.assertFalse(report["quota_observed"])
        self.assertEqual(report["quota_age_bucket"], "unknown")
        self.assertEqual(report["text_generations"], 0)

    def test_live_is_at_most_one_read_only_usage_call(self):
        proxy = FakeQuotaProxy(quota=quota(secondary=True))
        report = summarize_quota(proxy, usage_mode="live", now=NOW)
        self.assertEqual(proxy.calls, [("NEVER_PUBLIC_ACCOUNT_ID", False)])
        self.assertEqual(report["status"], "restriction_reported")
        self.assertEqual(report["secondary_window"], "limit_reported")
        self.assertEqual(report["read_only_usage_requests"], 1)
        self.assertNotIn("NEVER_PUBLIC_ACCOUNT_ID", json.dumps(report))

    def test_failed_live_usage_is_unknown_and_never_logs_provider_response(self):
        proxy = FakeQuotaProxy(quota=quota(), error="token=DO_NOT_LOG")
        report = summarize_quota(proxy, usage_mode="live", now=NOW)
        self.assertEqual(report["status"], "live_usage_unavailable")
        self.assertEqual(report["read_only_usage_requests"], 1)
        self.assertNotIn("DO_NOT_LOG", json.dumps(report))
        self.assertFalse(report["quota_observed"])

    def test_no_eligible_account_does_not_read_usage_or_switch_models(self):
        proxy = FakeQuotaProxy(eligible=False, quota=quota(primary=True))
        report = summarize_quota(proxy, usage_mode="live", now=NOW)
        self.assertEqual(report["status"], "no_eligible_account")
        self.assertEqual(report["sampled_accounts"], 0)
        self.assertEqual(report["read_only_usage_requests"], 0)
        self.assertEqual(proxy.calls, [])

    def test_stale_quota_cannot_be_reported_as_fresh(self):
        proxy = FakeQuotaProxy(quota=quota(timestamp=NOW-timedelta(days=4)))
        report = summarize_quota(proxy, now=NOW)
        self.assertEqual(report["quota_age_bucket"], "older_than_24_hours")
        self.assertEqual(report["status"], "no_restriction_reported")
        self.assertFalse(report["429_cause_proven"])

    def test_bad_accounts_response_is_rejected(self):
        class Proxy:
            def accounts(self): return {"accounts": ["bad"]}
        with self.assertRaisesRegex(ValueError, "QUOTA_ACCOUNTS_INVALID"):
            summarize_quota(Proxy())

    def test_live_cli_requires_owner_manual_dispatch(self):
        from videoforge.proxy.cli import run
        out = StringIO()
        with (mock.patch.dict(os.environ, {}, clear=True),
              redirect_stdout(out)):
            self.assertEqual(run(["--action", "quota", "--usage-mode", "live"]), 1)
        self.assertNotIn("NEVER_PUBLIC", out.getvalue())

    def test_cli_cached_is_local_and_sanitized(self):
        from videoforge.proxy.cli import run
        proxy = FakeQuotaProxy(quota=quota(primary=True))
        with (mock.patch("videoforge.proxy.cli.ProxyClient", return_value=proxy),
              redirect_stdout(StringIO()) as out):
            self.assertEqual(run(["--action", "quota"]), 0)
        report = json.loads(out.getvalue())
        self.assertEqual(report["status"], "restriction_reported")
        self.assertEqual(proxy.calls, [])

    def test_cli_live_uses_one_get_with_explicit_context(self):
        from videoforge.proxy.cli import run
        env = {
            "PROXY_QUOTA_LIVE_APPROVED": "yes",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": "HelioConde/video-forge-ia",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_RUN_ATTEMPT": "1",
        }
        proxy = FakeQuotaProxy(quota=quota())
        with (mock.patch.dict(os.environ, env, clear=True),
              mock.patch("videoforge.proxy.cli.ProxyClient", return_value=proxy),
              redirect_stdout(StringIO()) as out):
            self.assertEqual(run(["--action", "quota", "--usage-mode", "live"]), 0)
        self.assertEqual(len(proxy.calls), 1)
        self.assertEqual(json.loads(out.getvalue())["read_only_usage_requests"], 1)
