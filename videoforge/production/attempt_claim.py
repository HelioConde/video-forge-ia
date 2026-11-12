"""Persist a one-shot text-agent attempt in GitHub before calling Codex Proxy.

GitHub's create-file-only Contents API is the cross-run exclusive claim:
the same editorial fingerprint cannot be claimed twice. This is not a queue,
a proof of editorial quality, or a substitute for human review.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from videoforge.channel_agents.dedup import norm

REPOSITORY = "HelioConde/video-forge-ia"
RUN_ID = re.compile(r"^[0-9]{5,22}$")
TOPIC_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
SHA = re.compile(r"^[a-f0-9]{40}$")


class ClaimError(ValueError):
    """No provider payloads, tokens, or request data in raised errors."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _validated(plan: dict, context: dict, source_run_id: str) -> tuple[str, dict]:
    try:
        demand = plan["demand"]
        task = plan["tasks"][0]
        title = demand["tema"]
        topic_id = demand["id"]
        channel = demand["canal"]
        if (plan["schema"] != "videoforge/production-delegation/v1"
                or plan["publishing_enabled"] is not False
                or plan["execution_enabled"] is not False
                or task["id"] != "briefing"
                or task["responsavel"] != "coordenador-pautas"
                or context["status"] != "editorial_topic_reservation_verified"
                or context["channel"] != channel
                or context["title"] != title
                or not isinstance(title, str)
                or not 12 <= len(title) <= 220
                or not isinstance(topic_id, str)
                or not TOPIC_ID.fullmatch(topic_id)
                or channel != "otaku-br"
                or not isinstance(source_run_id, str)
                or not RUN_ID.fullmatch(source_run_id)
                or not isinstance(context["anime"], str)
                or not isinstance(context["angle"], str)):
            raise ValueError()
        topic_key = norm(" ".join((channel, context["anime"],
                                   title, context["angle"])))
        if len(topic_key) < 28:
            raise ValueError()
    except (TypeError, KeyError, IndexError, ValueError):
        raise ClaimError("CLAIM_UNVERIFIED_HANDOFF") from None
    digest = hashlib.sha256(topic_key.encode("utf-8")).hexdigest()
    path = "canal/otaku-br/editorial/tentativas/" + digest + ".json"
    return path, {
        "schema": "videoforge/one-shot-briefing-claim/v1",
        "channel": channel,
        "topic_id": topic_id,
        "source_run_id": source_run_id,
        "topic_sha256": digest,
        "task": "briefing",
        "role": "coordenador-pautas",
        "status": "attempt_reserved_no_automatic_retry",
        "model_calls_confirmed": False,
        "media_generated": False,
        "youtube_uploaded": False,
    }


def claim_one_briefing(*, plan: dict, context: dict, source_run_id: str,
                       run_id: str, token: str, env: dict,
                       opener=None) -> dict:
    """One GitHub create-only request; fail closed on conflict or uncertain result.

    A claim remains even if the provider subsequently fails or times out.
    Reconciliation must be manual: never auto-delete or auto-retry the claim.
    """
    if (not isinstance(env, dict)
            or env.get("GITHUB_REPOSITORY") != REPOSITORY
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or env.get("GITHUB_ACTOR") != "HelioConde"
            or env.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise ClaimError("CLAIM_RUNNER_NOT_AUTHORIZED")
    if (not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id)
            or not isinstance(token, str) or len(token) < 15):
        raise ClaimError("CLAIM_RUN_OR_TOKEN_INVALID")
    path, row = _validated(plan, context, source_run_id)
    row["workflow_run_id"] = run_id
    payload = {
        "message": "chore(agents): reserve one Otaku briefing attempt " + row["topic_sha256"][:12],
        "branch": "main",
        "content": base64.b64encode(
            (json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
        ).decode("ascii"),
    }
    req = Request(
        "https://api.github.com/repos/" + REPOSITORY + "/contents/" + path,
        method="PUT",
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "VideoForge-OneBriefing-Claim",
        },
    )
    try:
        with (opener or build_opener(_NoRedirect()).open)(req, timeout=20) as response:
            if response.status != 201:
                raise ClaimError("CLAIM_GITHUB_CREATE_NOT_CONFIRMED")
            raw = response.read(12000)
        value = json.loads(raw)
        if (not isinstance(value, dict)
                or value.get("content", {}).get("path") != path
                or not SHA.fullmatch(value.get("commit", {}).get("sha", ""))):
            raise ClaimError("CLAIM_GITHUB_RESPONSE_UNVERIFIED")
    except HTTPError as exc:
        if exc.code in (409, 422):
            raise ClaimError("CLAIM_ALREADY_RESERVED_OR_CONFLICT") from None
        raise ClaimError("CLAIM_GITHUB_HTTP_ERROR") from None
    except (URLError, TimeoutError, OSError, ValueError, TypeError):
        raise ClaimError("CLAIM_GITHUB_UNCERTAIN_DO_NOT_RETRY") from None
    # No topic title or credentials in return value.
    return {
        "schema": "videoforge/one-shot-briefing-claim-result/v1",
        "status": "attempt_reserved_no_automatic_retry",
        "path": path,
        "proxy_calls_sent": 0,
        "upload_enabled": False,
    }
