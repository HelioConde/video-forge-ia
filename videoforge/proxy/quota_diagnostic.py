"""Safe, bounded quota investigation for Codex Proxy HTTP 429.

Use ONLY an authenticated backend. Do not print admin records, OAuth details,
provider response bodies, balances, account identifiers or raw errors.
A cached quota cannot prove that a new generation will succeed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .client import ProxyError


def _when(value: object) -> datetime | None:
    if not isinstance(value, str) or len(value) > 50:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except ValueError:
        return None


def _freshness(value: object, now: datetime) -> str:
    timestamp = _when(value)
    if timestamp is None:
        return "unknown"
    age = (now - timestamp).total_seconds()
    if age < -300:
        return "unknown"
    if age <= 900:
        return "within_15_minutes"
    if age <= 86400:
        return "within_24_hours"
    return "older_than_24_hours"


def _limit(window: object) -> str:
    if not isinstance(window, dict):
        return "not_reported"
    if window.get("limit_reached") is True:
        return "limit_reported"
    # allowed=false can mean a provider restriction not proven to be quota
    if window.get("allowed") is False:
        return "not_allowed"
    return "not_reported"


def summarize_quota(proxy: Any, *, usage_mode: str = "cached",
                    now: datetime | None = None) -> dict:
    """One account sample and at most one explicit GET usage request.

    `usage_mode=live` MAY refresh OAuth as part of the read-only upstream
    status request. It NEVER sends /v1/chat/completions or images requests.
    """
    if usage_mode not in ("cached", "live"):
        raise ValueError("QUOTA_MODE_INVALID")
    now = now or datetime.now(timezone.utc)
    response = proxy.accounts()
    rows = response.get("accounts") if isinstance(response, dict) else None
    if not isinstance(rows, list) or len(rows) > 20 or any(not isinstance(x, dict) for x in rows):
        raise ValueError("QUOTA_ACCOUNTS_INVALID")

    eligible = [x for x in rows if x.get("eligible_now") is True]
    selected = eligible[0] if eligible else None
    # A valid but unavailable account may still expose a cooldown.
    active_cooldown = any(
        (expiry := _when(x.get("cooldown_until"))) is not None and expiry > now
        for x in rows
    )
    snapshot = None
    usage_available = False
    usage_requests = 0
    if selected:
        if usage_mode == "cached":
            snapshot = selected.get("cached_quota")
            usage_available = isinstance(snapshot, dict)
        else:
            # Never expose account ID; it is used solely inside this process.
            account_id = selected.get("id")
            if not isinstance(account_id, str) or not (1 <= len(account_id) <= 200):
                raise ValueError("QUOTA_ACCOUNT_ID_INVALID")
            usage_requests = 1
            try:
                usage = proxy.account_usage(account_id, cached=False)
                if isinstance(usage, dict):
                    snapshot = usage.get("quota_runtime")
                    usage_available = isinstance(snapshot, dict)
            except ProxyError:
                # Failed read-only GET is not evidence of no quota limits.
                usage_available = False
    primary = _limit(snapshot.get("rate_limit")) if isinstance(snapshot, dict) else "not_reported"
    secondary = _limit(snapshot.get("secondary_rate_limit")) if isinstance(snapshot, dict) else "not_reported"
    if not rows:
        state = "no_accounts"
    elif not eligible:
        state = "no_eligible_account"
    elif usage_mode == "live" and not usage_available:
        state = "live_usage_unavailable"
    elif not usage_available:
        state = "quota_not_observed"
    elif primary in ("limit_reported", "not_allowed") or secondary in ("limit_reported", "not_allowed"):
        state = "restriction_reported"
    elif active_cooldown:
        state = "cooldown_reported"
    else:
        state = "no_restriction_reported"

    # Keep all keys and value labels fixed, with no untrusted string output.
    return {
        "schema": "videoforge/proxy-quota-diagnostic/v1",
        "status": state,
        "usage_mode": usage_mode,
        "accounts_seen": len(rows),
        "eligible_accounts": len(eligible),
        "sampled_accounts": 1 if selected else 0,
        "cooldown_active": active_cooldown,
        "quota_observed": usage_available,
        "quota_age_bucket": (
            _freshness(snapshot.get("fetched_at"), now)
            if isinstance(snapshot, dict) else "unknown"
        ),
        "primary_window": primary,
        "secondary_window": secondary,
        "read_only_usage_requests": usage_requests,
        "text_generations": 0,
        "images_generated": 0,
        "videos_uploaded": 0,
        "429_cause_proven": False,
    }
