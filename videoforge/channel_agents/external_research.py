"""Public, source-linked context supplied by an external research assistant.

This is NOT a YouTube Analytics snapshot, a verified trending ranking, or an
autonomous worker result. No network requests, model calls or publishing.
"""
from __future__ import annotations

import argparse
from datetime import date
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


SCHEMA = "videoforge/external-editorial-research/v1"
NAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
CHANNEL = re.compile(r"^[a-z0-9][a-z0-9-]{1,50}$")


class ExternalResearchError(ValueError):
    """A stored research packet cannot be accepted safely."""


def _string(value: object, *, max_length: int) -> bool:
    return isinstance(value, str) and 1 <= len(value.strip()) <= max_length and (
        not any(ord(char) < 32 for char in value)
    )


def _source_url(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 500:
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            return False
        if parsed.port not in (None, 443) or parsed.fragment:
            return False
        if host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
        return "." in host and bool(re.fullmatch(r"[a-zA-Z0-9.-]+", host))
    except ValueError:
        return False


def validate_research(data: object, *, channel: str, channel_id: str,
                      as_of: date | None = None) -> dict:
    """Validate provenance and channel identity, not the factual truth of URLs.

    Source statements still need editorial fact-checking; this validator
    intentionally never fetches arbitrary third-party URLs.
    """
    today = as_of or date.today()
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ExternalResearchError("RESEARCH_SCHEMA_INVALID")
    if data.get("channel") != channel or data.get("channel_id") != channel_id:
        raise ExternalResearchError("RESEARCH_CHANNEL_MISMATCH")
    if data.get("prepared_by") != "chatgpt_external_research":
        raise ExternalResearchError("RESEARCH_PROVENANCE_INVALID")
    if data.get("scope") != "source_context_only":
        raise ExternalResearchError("RESEARCH_CANNOT_APPROVE_TOPIC")
    try:
        researched = date.fromisoformat(data["researched_on"])
        if researched > today:
            raise ValueError("future date")
    except (ValueError, KeyError, TypeError):
        raise ExternalResearchError("RESEARCH_DATE_INVALID") from None
    rows = data.get("signals")
    if not isinstance(rows, list) or not (1 <= len(rows) <= 12):
        raise ExternalResearchError("RESEARCH_SIGNAL_COUNT_INVALID")
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ExternalResearchError("RESEARCH_SIGNAL_INVALID")
        ident = row.get("id")
        if not isinstance(ident, str) or not IDENTIFIER.fullmatch(ident) or ident in ids:
            raise ExternalResearchError("RESEARCH_SIGNAL_ID_INVALID")
        ids.add(ident)
        if not all(_string(row.get(k), max_length=m) for k, m in (
                ("series", 110), ("verified_fact", 340),
                ("research_question", 240))):
            raise ExternalResearchError("RESEARCH_SIGNAL_TEXT_INVALID")
        aliases = row.get("title_aliases")
        if aliases is not None:
            if (not isinstance(aliases, list) or not (1 <= len(aliases) <= 8)
                    or any(not _string(alias, max_length=65)
                           or len(alias.strip()) < 3 for alias in aliases)
                    or len({alias.casefold().strip() for alias in aliases}) != len(aliases)):
                raise ExternalResearchError("RESEARCH_TITLE_ALIASES_INVALID")
        momentum = row.get("public_momentum")
        if momentum is not None:
            if (not isinstance(momentum, dict)
                    or set(momentum) != {"provider", "observed_on", "video_id",
                                        "views_per_hour", "observed_views"}
                    or momentum.get("provider") != "vidiq"
                    or momentum.get("observed_on") != data["researched_on"]
                    or not isinstance(momentum.get("video_id"), str)
                    or not re.fullmatch(r"[A-Za-z0-9_-]{11}", momentum["video_id"])
                    or type(momentum.get("observed_views")) is not int
                    or not 0 <= momentum["observed_views"] < 10 ** 12
                    or not isinstance(momentum.get("views_per_hour"), (int, float))
                    or isinstance(momentum["views_per_hour"], bool)
                    or not 0 <= momentum["views_per_hour"] < 1_000_000_000
                    or row.get("source", {}).get("url") !=
                    "https://www.youtube.com/watch?v=" + momentum["video_id"]):
                raise ExternalResearchError("RESEARCH_PUBLIC_MOMENTUM_INVALID")
        if row.get("editorial_status") != "unranked_requires_channel_metrics":
            raise ExternalResearchError("RESEARCH_SIGNAL_CANNOT_RANK")
        source = row.get("source")
        if (not isinstance(source, dict)
                or not _string(source.get("publisher"), max_length=120)
                or not _source_url(source.get("url"))):
            raise ExternalResearchError("RESEARCH_SOURCE_INVALID")
        try:
            published = date.fromisoformat(source["published_on"])
            if published > researched:
                raise ValueError("source published after research")
        except (ValueError, KeyError, TypeError):
            raise ExternalResearchError("RESEARCH_SOURCE_DATE_INVALID") from None
    return data


def latest_research(*, root: Path, channel: str, channel_id: str,
                    as_of: date | None = None) -> dict | None:
    """Return newest dated research packet; do not silently skip invalid files."""
    if not CHANNEL.fullmatch(channel):
        raise ExternalResearchError("RESEARCH_CHANNEL_INVALID")
    folder = root / "canal" / channel / "editorial" / "pesquisas"
    if not folder.exists():
        return None
    if folder.is_symlink() or not folder.is_dir():
        raise ExternalResearchError("RESEARCH_FOLDER_UNSAFE")
    today = as_of or date.today()
    candidates = sorted(
        (p for p in folder.iterdir()
         if NAME.fullmatch(p.name) and p.name[:10] <= today.isoformat()),
        key=lambda p: p.name, reverse=True,
    )
    if not candidates:
        return None
    path = candidates[0]
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 40_000:
        raise ExternalResearchError("RESEARCH_FILE_UNSAFE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise ExternalResearchError("RESEARCH_FILE_INVALID") from None
    if not isinstance(data, dict) or data.get("researched_on") != path.stem:
        raise ExternalResearchError("RESEARCH_FILENAME_DATE_MISMATCH")
    return validate_research(data, channel=channel, channel_id=channel_id,
                             as_of=today)


def fresh_research(*, root: Path, channel: str, channel_id: str,
                   as_of: date | None = None) -> dict:
    """Require ChatGPT public research performed today or yesterday.

    Stale content cannot be represented as a current trend. This helper does
    not call the network, OAuth, Codex Proxy, or generate any media.
    """
    today = as_of or date.today()
    data = latest_research(root=root, channel=channel, channel_id=channel_id,
                           as_of=today)
    if data is None or (today - date.fromisoformat(data["researched_on"])).days > 1:
        raise ExternalResearchError("RESEARCH_FRESH_CONTEXT_REQUIRED")
    return data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validar pesquisa externa; sem Proxy.")
    parser.add_argument("--channel", choices=("otaku-br",), required=True)
    args = parser.parse_args(argv)
    from .manager import ROOT, channel_policy
    policy = channel_policy(args.channel)
    research = latest_research(root=ROOT, channel=args.channel,
                               channel_id=policy["youtube_channel_id"])
    if research is None:
        raise SystemExit("RESEARCH_PACKET_NOT_FOUND")
    print("EXTERNAL_RESEARCH_VALIDATED_" + str(len(research["signals"])) + "_SIGNALS")
    print("NO_YOUTUBE_METRICS_NO_PROXY_CALLS_NO_PUBLICATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
