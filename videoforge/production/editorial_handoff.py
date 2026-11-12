"""Validated handoff: real editor-agent research -> reserved topic -> briefing.

No model, media, or publishing call is made by this module.
The GitHub runner must separately validate the source workflow run and
human-authorized job before trusting the downloaded editorial report.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from videoforge.channel_agents.manager import channel_policy
from videoforge.channel_agents.dedup import norm
from .dispatcher import ROOT, build_plan
from .agent_dispatch import plan_text_dispatch

_RUN_ID = re.compile(r"^[0-9]{5,22}$")
_TOPIC_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
_APPROVAL = "approved_reserved"


class HandoffError(ValueError):
    """Human-readable status code, never model content or credentials."""


def _read_report(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        raise HandoffError("HANDOFF_REPORT_MISSING_OR_UNSAFE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise HandoffError("HANDOFF_REPORT_JSON_INVALID") from None
    if not isinstance(data, dict):
        raise HandoffError("HANDOFF_REPORT_SCHEMA_INVALID")
    return data


def prepare_editorial_handoff(report: dict, *, source_run_id: str,
                              root: Path = ROOT, channel: str = "otaku-br") -> dict:
    """Produce a safe, READY-only draft request without executing the agent.

    Requiring an external reservation is deliberate: a suggested topic is
    NOT permission to use quotas or to create a production job.
    """
    if not isinstance(source_run_id, str) or not _RUN_ID.fullmatch(source_run_id):
        raise HandoffError("HANDOFF_SOURCE_RUN_ID_INVALID")
    if channel != "otaku-br":
        raise HandoffError("HANDOFF_PILOT_ONLY_OTAKU_BR")
    policy = channel_policy(channel, root=root)
    if not isinstance(report, dict) or any((
        report.get("schema") != "videoforge/editorial-team/v1",
        report.get("channel") != channel,
        report.get("channel_id") != policy["youtube_channel_id"],
        report.get("status") != "awaiting_editorial_review_and_reservation",
        report.get("decision_authority") != policy["name"],
        report.get("topic_provenance") != "codex_proxy_researcher_plus_real_youtube_analytics",
        report.get("choices_from_assistant") != 0,
        report.get("requires_human_editorial_review") is not True,
        report.get("requires_topic_reservation") is not True,
        report.get("proxy_calls") != 1,
        report.get("images_generated") != 0,
        report.get("video_generated") is not False,
        report.get("upload_enabled") is not False,
    )):
        raise HandoffError("HANDOFF_UNVERIFIED_EDITORIAL_DECISION")
    topic = report.get("chosen_topic")
    if not isinstance(topic, dict):
        raise HandoffError("HANDOFF_TOPIC_MISSING")
    topic_id, title = topic.get("id"), topic.get("title")
    if (not isinstance(topic_id, str) or not _TOPIC_ID.fullmatch(topic_id)
            or not isinstance(title, str) or not 12 <= len(title.strip()) <= 220):
        raise HandoffError("HANDOFF_TOPIC_FIELDS_INVALID")
    anime = topic.get("anime")
    if not isinstance(anime, str) or not 2 <= len(anime) <= 120:
        raise HandoffError("HANDOFF_ANIME_INVALID")
    if any(norm(anime) == norm(p) or norm(anime).startswith(norm(p) + " ")
           for p in policy.get("paused_animes", [])):
        raise HandoffError("HANDOFF_ANIME_PAUSED")
    duration = topic.get("duration_seconds")
    if not isinstance(duration, int) or isinstance(duration, bool) or not 30 <= duration <= 3600:
        raise HandoffError("HANDOFF_DURATION_INVALID")
    angle = topic.get("angle")
    if not isinstance(angle, str) or not 3 <= len(angle) <= 220:
        raise HandoffError("HANDOFF_ANGLE_INVALID")
    deputy = report.get("deputy")
    if not isinstance(deputy, dict) or deputy.get("role") != "subgerente":
        raise HandoffError("HANDOFF_DEPUTY_AUDIT_MISSING")
    audits = deputy.get("candidates")
    if (not isinstance(audits, list)
            or len([item for item in audits if isinstance(item, dict)
                    and item.get("candidate_id") == topic_id
                    and item.get("accepted") is True]) != 1):
        raise HandoffError("HANDOFF_TOPIC_NOT_DEPUTY_APPROVED")
    proposals = report.get("proposals")
    if (not isinstance(proposals, list)
            or len([item for item in proposals if isinstance(item, dict)
                    and item.get("id") == topic_id and item.get("title") == title
                    and item.get("status") == "eligible_for_manager_ranking"]) != 1):
        raise HandoffError("HANDOFF_MANAGER_CHOICE_MISMATCH")

    # A separate, persistent, reviewed topic reservation is mandatory.
    ledger = _read_report(root / "canal" / channel / "editorial" / "reservas.json")
    if (ledger.get("schema") != "videoforge/channel-topic-reservations/v1"
            or ledger.get("channel") != channel
            or ledger.get("channel_id") != policy["youtube_channel_id"]):
        raise HandoffError("HANDOFF_RESERVATION_LEDGER_INVALID")
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        raise HandoffError("HANDOFF_RESERVATIONS_INVALID")
    matching = [entry for entry in entries if isinstance(entry, dict)
                and entry.get("id") == topic_id
                and entry.get("source_run_id") == source_run_id
                and entry.get("titulo_provisorio") == title
                and entry.get("status") == _APPROVAL
                and entry.get("human_approved") is True]
    if len(matching) != 1:
        raise HandoffError("HANDOFF_APPROVED_RESERVATION_REQUIRED")

    plan = build_plan({
        "id": topic_id, "canal": channel,
        "tema": title, "duracao_segundos": duration,
    }, root=root)
    ready = plan_text_dispatch(plan, root=root)["ready_text_agents"]
    if len(ready) != 1 or ready[0]["task_id"] != "briefing" or ready[0]["role_id"] != "coordenador-pautas":
        raise HandoffError("HANDOFF_BRIEFING_NOT_READY")
    sources = topic.get("sources_to_verify", [])
    if not isinstance(sources, list):
        sources = []
    context = {
        "status": "editorial_topic_reservation_verified",
        "channel": channel,
        "title": title,
        "anime": anime,
        "angle": angle,
        "genre": str(topic.get("genre", ""))[:100],
        "format": str(topic.get("format", ""))[:100],
        "duration_seconds": duration,
        "rationale_is_hypothesis_not_verified_fact": str(topic.get("rationale", ""))[:1200],
        "sources_to_verify_not_yet_verified": [str(s)[:240] for s in sources[:10]],
        "constraints": [
            "Original script, no repeated topic",
            "Verify facts and source material before production",
            "No video generation and no YouTube upload",
        ],
    }
    serialized = json.dumps(context, ensure_ascii=False)
    if len(serialized) > 16000:
        raise HandoffError("HANDOFF_CONTEXT_TOO_LONG")
    return {
        "schema": "videoforge/editorial-briefing-handoff/v1",
        "source_run_id": source_run_id,
        "plan": plan,
        "task_id": "briefing",
        "context": serialized,
        "proxy_requests_sent": 0,
        "human_approved_reservation_verified": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validar pauta reservada, sem consumir IA")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists() or args.output_dir.is_symlink():
        raise SystemExit("HANDOFF_OUTPUT_DIR_MUST_NOT_EXIST")
    data = prepare_editorial_handoff(_read_report(args.report),
                                     source_run_id=args.source_run_id)
    args.output_dir.mkdir(parents=True, mode=0o700)
    args.output_dir.chmod(0o700)
    for filename, obj in (("plan.json", data["plan"]),
                          ("context.json", json.loads(data["context"]))):
        path = args.output_dir / filename
        with path.open("x", encoding="utf-8") as stream:
            json.dump(obj, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        path.chmod(0o600)
    print("HANDOFF_READY_FOR_ONE_APPROVED_BRIEFING_NO_PROXY_CALLS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
