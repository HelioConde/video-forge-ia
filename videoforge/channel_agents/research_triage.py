"""Offline evidence coverage for external research, never a selected topic.

Cross-checks public research signals against actual YouTube upload titles and
a read-only Analytics snapshot. It never creates new candidates, uses the Codex
Proxy, generates media, records reservations or authorizes publishing.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .dedup import norm
from .external_research import latest_research, validate_research
from .manager import ROOT, channel_policy
from .strategy import analyse_performance
from .youtube import YouTubeReadOnly, oauth_access_token


class ResearchTriageError(ValueError):
    pass


def _matched_title(title: str, keywords: list[str]) -> bool:
    """Whole-token phrase checks, NOT semantic duplicate detection."""
    words = " " + norm(title) + " "
    return any(" " + norm(alias) + " " in words for alias in keywords)


def triage_research(*, research: dict, snapshot: dict, policy: dict) -> dict:
    """Report source coverage without a candidate, rank, winner or prediction."""
    channel = policy["channel"] if "channel" in policy else policy["id"]
    channel_id = policy["youtube_channel_id"]
    validate_research(research, channel=channel, channel_id=channel_id)
    if (snapshot.get("schema") != "videoforge/channel-research/v1"
            or snapshot.get("source") != "youtube-data-v3+analytics-v2"
            or snapshot.get("channel_id") != channel_id
            or snapshot.get("read_only") is not True
            or snapshot.get("history_complete") is not True
            or not isinstance(snapshot.get("videos"), list)
            or snapshot.get("count") != len(snapshot["videos"])):
        raise ResearchTriageError("TRIAGE_VERIFIED_HISTORY_REQUIRED")

    metrics = analyse_performance(snapshot)
    results = []
    for signal in research["signals"]:
        # Explicit aliases supplied as search hints, never metrics or rankings.
        aliases = signal.get("title_aliases") or [signal["series"].split("—")[0].strip()]
        matching = [
            video for video in snapshot["videos"]
            if _matched_title(str(video.get("title") or ""), aliases)
        ]
        eligible = [
            video for video in matching
            if isinstance(video.get("metrics"), dict)
            and isinstance(video["metrics"].get("views"), (int, float))
            and not isinstance(video["metrics"]["views"], bool)
            and video["metrics"]["views"] >= 25
            and isinstance(video["metrics"].get("averageViewPercentage"), (int, float))
            and not isinstance(video["metrics"]["averageViewPercentage"], bool)
        ]
        results.append({
            "signal_id": signal["id"],
            "series": signal["series"],
            "source_url": signal["source"]["url"],
            "series_title_mentions": len(matching),
            "analytics_samples_with_minimum_fields": len(eligible),
            "title_keyword_method": "heuristic_non_exhaustive",
            "topic_uniqueness": "not_verified_no_candidate_provided",
            "status": "awaiting_independent_research_and_editorial_audit",
        })

    return {
        "schema": "videoforge/external-research-triage/v1",
        "channel": channel,
        "channel_id": channel_id,
        "researched_on": research["researched_on"],
        "youtube_window": snapshot.get("window"),
        "verified_full_upload_history": True,
        "verified_read_only_snapshot": True,
        "overall_duration_evidence_confidence": metrics["confidence"],
        "signals": results,
        "decision_authority": "Gerente do canal apos auditoria do Subgerente",
        "selected": None,
        "candidates_created": 0,
        "topics_reserved": 0,
        "proxy_calls": 0,
        "images_generated": 0,
        "videos_generated": 0,
        "publish_enabled": False,
        "requires_independent_research": True,
        "requires_human_editorial_review": True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Triagem read-only de fontes externas.")
    parser.add_argument("--channel", choices=("otaku-br",), required=True)
    parser.add_argument("--mode", choices=("offline", "youtube-readonly"),
                        default="offline")
    parser.add_argument("--days", type=int, default=90, choices=(28, 90, 180))
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    policy = channel_policy(args.channel)
    research = latest_research(root=ROOT, channel=args.channel,
                               channel_id=policy["youtube_channel_id"])
    if research is None:
        raise SystemExit("TRIAGE_RESEARCH_NOT_FOUND")

    if args.mode == "youtube-readonly":
        if (os.getenv("CHANNEL_METRICS_READONLY_AUTHORIZED") != "yes"
                or os.getenv("GITHUB_EVENT_NAME") != "workflow_dispatch"
                or os.getenv("GITHUB_REPOSITORY") != "HelioConde/video-forge-ia"
                or os.getenv("GITHUB_REF") != "refs/heads/main"
                or os.getenv("GITHUB_RUN_ATTEMPT") != "1"):
            raise SystemExit("TRIAGE_PRIVATE_READONLY_NOT_AUTHORIZED")
        token = oauth_access_token(os.getenv("YOUTUBE_CLIENT_JSON", ""),
                                   os.getenv("YOUTUBE_CHANNEL_TOKEN_JSON", ""))
        snapshot = YouTubeReadOnly(
            access_token=token,
            expected_channel_id=policy["youtube_channel_id"],
        ).snapshot(days=args.days)
    else:
        if args.inventory is None or not args.inventory.is_file() or args.inventory.is_symlink():
            raise SystemExit("TRIAGE_OFFLINE_INVENTORY_REQUIRED")
        if args.inventory.stat().st_size > 2_000_000:
            raise SystemExit("TRIAGE_OFFLINE_INVENTORY_UNSAFE")
        snapshot = json.loads(args.inventory.read_text(encoding="utf-8"))

    result = triage_research(research=research, snapshot=snapshot, policy=policy)
    if args.output.is_symlink() or args.output.exists():
        raise SystemExit("TRIAGE_OUTPUT_ALREADY_EXISTS")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    # Never print private Analytics metrics, titles, or tokens in public logs.
    print("TRIAGE_READONLY_COMPLETE_" + str(len(result["signals"])) + "_SIGNALS")
    print("ZERO_PROXY_CALLS_ZERO_TOPICS_SELECTED_ZERO_IMAGES_ZERO_UPLOADS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
