"""Delegated editorial research: research agent proposes, manager selects, deputy audits.

No fixed anime/topic/title in Python. All suggestions originate from the
authorized LLM researcher using real channel analytics + public trend metadata.
The manager uses existing deterministic ranking and anti-duplication policy.
The deputy independently verifies selected proposal and guardrails.

This only chooses a DRAFT TOPIC, never requests images, renders, or publishes.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
from contextlib import nullcontext

from videoforge.production.role_events import CheckReporter, role_task

from videoforge.proxy.client import ProxyClient
from .dedup import DuplicateTopic, assert_unique, editorial_fingerprint, norm
from .ideation import EditorialIdeationError, propose_candidates
from .manager import ROOT, build_editorial_plan, channel_policy
from .strategy import analyse_performance
from .youtube import YouTubeReadOnly, YouTubeReadError, oauth_access_token
from .external_research import (ExternalResearchError, fresh_research,
                                validate_research)


class EditorialTeamError(ValueError):
    pass


def public_discovery_queries(*, snapshot: dict, research: dict,
                             paused_animes: list[str]) -> list[str]:
    """Dynamic PUBLIC search subjects, not topics selected for production."""
    paused = [norm(x) for x in paused_animes]
    ranked = []
    for position, signal in enumerate(research["signals"]):
        series = norm(signal["series"])
        if any(series == x or series.startswith(x + " ") for x in paused):
            continue
        aliases = signal.get("title_aliases") or [signal["series"]]
        terms = [norm(x) for x in aliases]
        score = 0
        for video in snapshot.get("videos", []):
            title = " " + norm(video.get("title", "")) + " "
            if not any((" " + term + " ") in title for term in terms if term):
                continue
            metrics = video.get("metrics")
            engaged = metrics.get("engagedViews") if isinstance(metrics, dict) else None
            if (isinstance(engaged, (int, float)) and not isinstance(engaged, bool)
                    and 0 <= engaged < 10 ** 12):
                score = max(score, engaged)
        query = max((alias for alias in aliases if 3 <= len(alias) <= 70),
                    key=len, default="")
        if query:
            ranked.append((-score, position, query))
    ranked.sort()
    selected = []
    seen = set()
    for _, _, query in ranked:
        key = norm(query)
        if key not in seen:
            selected.append(query)
            seen.add(key)
        if len(selected) == 2:
            break
    if not selected:
        raise EditorialTeamError("TEAM_NO_FRESH_PUBLIC_DISCOVERY_QUERY")
    return selected


def _read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        raise EditorialTeamError("EDITORIAL_INPUT_UNSAFE")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except (OSError, ValueError, UnicodeError):
        raise EditorialTeamError("EDITORIAL_INPUT_INVALID") from None


def audit_candidates(*, proposals: list[dict], snapshot: dict,
                     reservations: dict, manager: dict) -> dict:
    """Deputy works from the independently verified inventory, not model claims."""
    if not snapshot.get("history_complete") or snapshot.get("channel_id") != manager["youtube_channel_id"]:
        raise EditorialTeamError("DEPUTY_CHANNEL_INVENTORY_INVALID")
    if reservations.get("channel_id") != snapshot["channel_id"]:
        raise EditorialTeamError("DEPUTY_RESERVATIONS_CHANNEL_MISMATCH")
    paused = [norm(item) for item in manager.get("paused_animes", [])]
    checked = []
    seen_keys = set()
    for candidate in proposals:
        item = {"candidate_id": candidate.get("id"), "accepted": False}
        anime = norm(candidate.get("anime", ""))
        key = editorial_fingerprint(candidate)
        if any(anime == name or anime.startswith(name + " ") for name in paused):
            item["reason"] = "PAUSED_ANIME"
        elif key in seen_keys:
            item["reason"] = "DUPLICATE_IN_RESEARCH_BATCH"
        else:
            try:
                assert_unique(candidate, inventory=snapshot, reservations=reservations)
                item["accepted"] = True
                item["reason"] = "PASSED_HEURISTIC_DEDUP_CHECK"
                seen_keys.add(key)
            except DuplicateTopic as exc:
                item["reason"] = str(exc)
        checked.append(item)
    return {
        "role": "subgerente",
        "executor": "independent_deterministic_audit",
        "evaluated": len(checked),
        "accepted": sum(x["accepted"] for x in checked),
        "candidates": checked,
        "does_not_award_staff_points_without_work_evidence": True,
        "checks_editorial_uniqueness_further": True,
    }


def run_team(*, channel: str, snapshot: dict, trends: dict | None = None,
             external_research: dict | None = None,
             client: ProxyClient, model: str, root: Path = ROOT,
             stage_dir: Path | None = None, reporter: CheckReporter | None = None) -> dict:
    """Separate researcher LLM, analytics worker, manager, deputy QA tasks."""
    manager = channel_policy(channel, root=root)
    if external_research is not None:
        validate_research(external_research, channel=channel,
                          channel_id=manager["youtube_channel_id"])
    if snapshot.get("source") != "youtube-data-v3+analytics-v2":
        raise EditorialTeamError("TEAM_REQUIRES_VERIFIED_YOUTUBE_DATA")
    if snapshot.get("channel_id") != manager["youtube_channel_id"]:
        raise EditorialTeamError("TEAM_CHANNEL_ID_MISMATCH")
    if not snapshot.get("history_complete") or snapshot.get("count") != len(snapshot.get("videos", [])):
        raise EditorialTeamError("TEAM_FULL_UPLOAD_HISTORY_REQUIRED")
    if not snapshot.get("read_only"):
        raise EditorialTeamError("TEAM_READ_ONLY_SNAPSHOT_REQUIRED")
    reservations = _read_json(root / "canal" / channel / "editorial" / "reservas.json")
    if reservations.get("channel_id") != snapshot["channel_id"]:
        raise EditorialTeamError("TEAM_RESERVATIONS_ID_MISMATCH")
    if trends is not None and (
        not isinstance(trends, dict) or trends.get("read_only") is not True
        or trends.get("schema") != "videoforge/trend-signals/v1"
    ):
        raise EditorialTeamError("TEAM_TRENDS_SOURCE_INVALID")

    # 1. Data analyst: checks the exact channel and calculates duration evidence.
    analytics = analyse_performance(snapshot)
    if analytics.get("usable_samples", 0) < 3:
        raise EditorialTeamError("TEAM_INSUFFICIENT_VERIFIED_METRICS")

    # Emit check runs only with real evidence files on protected runner.
    def stage_file(name, value):
        if stage_dir is None:
            return
        stage_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = stage_dir / (name + ".json")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    def role_context(role, name):
        if stage_dir is None:
            return nullcontext()
        return role_task(role, evidence=(stage_dir / (name + ".json"),), reporter=reporter)

    # 2. A genuine LLM researcher produces candidate topics; none are seeded
    #    as fixed themes by this assistant, the manager or the runner.
    with role_context("roteirista", "research"):
        proposals = propose_candidates(
            manager=manager, snapshot=snapshot, reservations=reservations,
            trends=trends, external_research=external_research,
            client=client, model=model, authorized=True
        )
        stage_file("research", {"produced": len(proposals),
                                "topic_ids": [p["id"] for p in proposals],
                                "generator": "codex_proxy_chat",
                                "external_research_signals": len((external_research or {}).get("signals", [])),
                                "not_preselected_by_assistant": True})
    if not proposals:
        raise EditorialTeamError("TEAM_RESEARCHER_EMPTY_RESULT")

    # 3. Deputy: independent gate before any manager ranking.
    with role_context("subgerente", "audit"):
        deputy = audit_candidates(
            proposals=proposals, snapshot=snapshot, reservations=reservations,
            manager=manager
        )
        stage_file("audit", {"role": "subgerente",
                             "evaluated": deputy["evaluated"],
                             "accepted": deputy["accepted"],
                             "checks": deputy["candidates"]})
    accepted_ids = {row["candidate_id"] for row in deputy["candidates"] if row["accepted"]}
    safe_proposals = [item for item in proposals if item["id"] in accepted_ids]
    if not safe_proposals:
        return {
            "schema": "videoforge/editorial-team/v1", "channel": channel,
            "channel_id": manager["youtube_channel_id"],
            "status": "no_unique_candidate",
            "metrics": {"usable_samples": analytics["usable_samples"],
                        "duration_confidence": analytics["confidence"]},
            "agent_work": [
                {"agent": "analista-de-audiencia", "executor": "youtube_analytics",
                 "status": "completed"},
                {"agent": "pesquisador-de-pautas", "executor": "codex_proxy_chat",
                 "status": "completed"},
                {"agent": "subgerente", "executor": "verification_code",
                 "status": "completed"},
                {"agent": manager["name"], "executor": "ranking_code",
                 "status": "blocked_no_unique_candidate"},
            ],
            "deputy": deputy,
            "chosen_topic": None, "choices_from_assistant": 0,
            "proxy_calls": 1, "images_generated": 0, "upload_enabled": False,
        }

    # 4. Channel MANAGER is the only component authorized to select a theme.
    with role_context("diretor", "manager"):
        plan = build_editorial_plan(
            channel, snapshot=snapshot, candidate_rows=safe_proposals, root=root
        )
        stage_file("manager", {
            "role": "gerente-canal", "status": plan["status"],
            "chosen_id": (plan.get("selected") or {}).get("id"),
            "from_submanager_accepted_candidates": True,
            "not_chosen_by_assistant": True})
    selected = plan.get("selected")
    if selected is not None:
        if selected.get("id") not in accepted_ids:
            raise EditorialTeamError("MANAGER_CHOICE_NOT_DEPUTY_APPROVED")
        # Deputy double-checks the exact selected topic.
        confirm = audit_candidates(
            proposals=[selected], snapshot=snapshot,
            reservations=reservations, manager=manager
        )
        if confirm["accepted"] != 1:
            raise EditorialTeamError("DEPUTY_REJECTED_MANAGER_CHOICE")

    status = plan.get("status")
    return {
        "schema": "videoforge/editorial-team/v1",
        "channel": channel, "channel_id": manager["youtube_channel_id"],
        "status": status,
        "decision_authority": manager["name"],
        "topic_provenance": "codex_proxy_researcher_plus_real_youtube_analytics",
        "choices_from_assistant": 0,
        "metrics": {
            "usable_samples": analytics["usable_samples"],
            "duration_confidence": analytics["confidence"],
            "best_duration_bucket": analytics["best_duration_bucket"],
        },
        "agent_work": [
            {"agent": "analista-de-audiencia", "executor": "youtube_analytics",
             "status": "completed"},
            {"agent": "pesquisador-de-pautas", "executor": "codex_proxy_chat",
             "status": "completed", "suggested": len(proposals)},
            {"agent": "subgerente", "executor": "verification_code",
             "status": "completed", "accepted": deputy["accepted"]},
            {"agent": manager["name"], "executor": "ranking_code",
             "status": "completed" if selected else "blocked"},
        ],
        "deputy": deputy,
        "proposals": [{
            "id": p["id"],
            "anime": p["anime"], "title": p["titulo_provisorio"],
            "status": "eligible_for_manager_ranking" if p["id"] in accepted_ids else
                      "rejected_by_deputy",
        } for p in proposals],
        "chosen_topic": ({
            "id": selected["id"], "anime": selected["anime"],
            "title": selected["titulo_provisorio"],
            "angle": selected["abordagem"], "genre": selected["genero"],
            "format": selected["formato"],
            "duration_seconds": selected["duracao_segundos"],
            "rationale": selected.get("justificativa", "hypothesis_pending_review"),
            "sources_to_verify": selected.get("fontes_a_verificar", []),
        } if selected else None),
        "metrics_evidence": plan.get("evidence", {}),
        "requires_human_editorial_review": True,
        "requires_topic_reservation": True,
        "calls_sent": 1, "proxy_calls": 1,
        "images_generated": 0,
        "video_generated": False,
        "upload_enabled": False,
    }


# Actual text-model names published by the pinned Codex Proxy at
# 10/chatgpt-codex-proxy@1da5476 (internal/models/bootstrap.go).
# Do not infer that an advertised image model supports chat completions.
EDITORIAL_TEXT_MODEL_PREFERENCE = (
    "gpt-6.1-sol", "gpt-6-sol", "gpt-6.1-terra", "gpt-6-luna",
    "gpt-6-astra", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna",
)


def select_editorial_model(catalog: object) -> str:
    """Select from the real private Proxy catalogue, never invent a model.

    A model listed by /v1/models is not proof of quota/eligibility:
    actual chat call may still fail closed without retrying.
    """
    if not isinstance(catalog, dict) or not isinstance(catalog.get("data"), list):
        raise EditorialTeamError("TEAM_MODEL_CATALOG_INVALID")
    available = {
        item["id"] for item in catalog["data"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for model in EDITORIAL_TEXT_MODEL_PREFERENCE:
        if model in available:
            return model
    raise EditorialTeamError("TEAM_NO_SUPPORTED_EDITORIAL_MODEL")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Equipe escolhe pauta, assistente nao.")
    parser.add_argument("--channel", default="otaku-br")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args(argv)
    if (os.getenv("CHANNEL_IDEATION_APPROVED") != "yes"
            or os.getenv("GITHUB_REPOSITORY") != "HelioConde/video-forge-ia"
            or os.getenv("GITHUB_REF") != "refs/heads/main"
            or os.getenv("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or os.getenv("GITHUB_ACTOR") != "HelioConde"
            or os.getenv("GITHUB_RUN_ATTEMPT") != "1"):
        raise SystemExit("TEAM_PRIVATE_RESEARCH_APPROVAL_REQUIRED")
    if args.channel != "otaku-br":
        raise SystemExit("TEAM_PILOT_ONLY_OTAKU_BR")
    if not 28 <= args.days <= 180:
        raise SystemExit("TEAM_WINDOW_INVALID")
    try:
        policy = channel_policy(args.channel)
        # Reject stale or absent ChatGPT research before reading private YouTube
        # data or making a single generative call. A commit never starts research.
        external_research = fresh_research(
            root=ROOT, channel=args.channel, channel_id=policy["youtube_channel_id"],
            as_of=date.today())
        token = oauth_access_token(os.getenv("YOUTUBE_CLIENT_JSON", ""),
                                   os.getenv("YOUTUBE_CHANNEL_TOKEN_JSON", ""))
        yt = YouTubeReadOnly(access_token=token,
                             expected_channel_id=policy["youtube_channel_id"])
        snapshot = yt.snapshot(days=args.days)
        queries = public_discovery_queries(
            snapshot=snapshot, research=external_research,
            paused_animes=policy.get("paused_animes", []))
        trends = yt.trend_signals(queries, max_queries=2)
        if external_research is not None:
            print("EXTERNAL_RESEARCH_LOADED_" +
                  str(len(external_research["signals"])) + "_SIGNALS_CONTEXT_ONLY")
        proxy = ProxyClient(timeout=180)
        model = args.model
        if model == "auto":
            model = select_editorial_model(proxy.models())
        stage = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "videoforge-editorial-stage"
        report = run_team(channel=args.channel, snapshot=snapshot, trends=trends,
                          external_research=external_research,
                          client=proxy, model=model,
                          stage_dir=stage,
                          reporter=CheckReporter(channel=args.channel,
                                                 workflow_kind="editorial"))
        output = args.output
        if output.exists() or output.is_symlink():
            raise EditorialTeamError("TEAM_OUTPUT_ALREADY_EXISTS")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print("EDITORIAL_TEAM_DECISION_" + str(report["status"]).upper())
        print("TOPIC_CHOSEN_BY_MANAGER_NOT_CHATGPT")
        print("NO_IMAGES_NO_VIDEO_NO_PUBLISH")
        return 0 if report.get("chosen_topic") else 2
    except (EditorialTeamError, EditorialIdeationError,
            ExternalResearchError, YouTubeReadError) as exc:
        # Only local, fixed policy codes can be printed. Never disclose the
        # OAuth response, model output, HTTP error body, token or prompt.
        # Error class alone hides whether the block is insufficient channel
        # metrics, a missing model or a dedup restriction.
        code = str(exc)
        # Both exception classes use local fixed, ASCII-only rejection
        # codes. Never print upstream Proxy/OAuth/provider messages.
        if not isinstance(exc, (EditorialTeamError, EditorialIdeationError,
                                    ExternalResearchError)) or not (
                5 <= len(code) <= 90 and
                all(ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in code)):
            code = type(exc).__name__
        print("EDITORIAL_TEAM_BLOCKED_" + code)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
