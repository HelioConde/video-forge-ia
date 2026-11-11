"""Pontuação editorial transparente, por canal e com dados reais do YouTube.

O sistema faz recomendações condicionais; não garante alcance nem substitui QA
editorial. Sem Analytics ou inventário completo => recusa escolher pautas.
"""
from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any
from .dedup import assert_unique, editorial_fingerprint, DuplicateTopic, norm


def duration_bucket(seconds: int | None) -> str | None:
    if not isinstance(seconds, int) or seconds <= 0:
        return None
    if seconds <= 90:
        return "ate-90s"
    if seconds <= 180:
        return "91-180s"
    if seconds <= 600:
        return "3-10min"
    return "mais-10min"


def _number(value: Any) -> float | None:
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        try:
            n = float(value)
        except (ValueError, OverflowError):
            return None
        if n >= 0 and n < 10**12:
            return n
    return None


def _performance(video: dict) -> dict | None:
    metrics = video.get("metrics") or {}
    if not isinstance(metrics, dict):
        return None
    views = _number(metrics.get("views"))
    retention = _number(metrics.get("averageViewPercentage"))
    avg = _number(metrics.get("averageViewDuration"))
    length = video.get("duration_seconds")
    if views is None or retention is None or avg is None or not isinstance(length, int) or length <= 0:
        return None
    if views < 25:  # evita escolher formato por amostras irrisórias
        return None
    # Retenção pode ultrapassar 100% quando há repetição. Não interpretar como 100% garantido.
    return {
        "views": views,
        "retention": min(retention, 150) / 100,
        "watch_fraction": min(avg / length, 1.5),
        "duration_bucket": duration_bucket(length),
        "duration_seconds": length,
    }


def analyse_performance(snapshot: dict) -> dict:
    if (snapshot.get("schema") != "videoforge/channel-research/v1"
            or snapshot.get("history_complete") is not True
            or snapshot.get("count") != len(snapshot.get("videos", []))
            or not snapshot.get("channel_id")):
        raise ValueError("Snapshot YouTube incompleto")
    scored = [
        (video["id"], p)
        for video in snapshot["videos"] if (p := _performance(video))
    ]
    if not scored:
        return {"usable_samples": 0, "recommended_duration_seconds": None,
                "best_duration_bucket": None, "duration_evidence": [],
                "confidence": "insufficient_data"}
    groups: dict[str, list] = {}
    for video_id, p in scored:
        groups.setdefault(p["duration_bucket"], []).append((video_id, p))
    evidence = []
    for key, rows in groups.items():
        average_views = sum(p["views"] for _, p in rows) / len(rows)
        retention = median(p["retention"] for _, p in rows)
        watch = median(p["watch_fraction"] for _, p in rows)
        # Views comparadas na MESMA janela Analytics e equilíbrio de watch/retention.
        # Reduz o peso de grupo com menos de 3 vídeos.
        weight = min(len(rows) / 3, 1)
        evidence.append({
            "bucket": key, "samples": len(rows),
            "median_views": round(median(p["views"] for _, p in rows), 1),
            "median_retention_pct": round(retention * 100, 1),
            "median_watch_fraction": round(watch, 3),
            "score": round((.45 * min(average_views / 1000, 3)
                            + .35 * retention + .20 * watch) * weight, 4),
            "median_duration_seconds": int(median(p["duration_seconds"] for _, p in rows)),
        })
    ranked = sorted(evidence, key=lambda x: (x["score"], x["samples"]), reverse=True)
    winner = ranked[0]
    confidence = "supported" if winner["samples"] >= 3 else "exploratory"
    return {
        "usable_samples": len(scored),
        "best_duration_bucket": winner["bucket"] if confidence == "supported" else None,
        "recommended_duration_seconds": (
            winner["median_duration_seconds"] if confidence == "supported" else None
        ),
        "duration_evidence": ranked, "confidence": confidence,
    }


def select_idea(*, snapshot: dict, reservations: dict, candidates: list[dict],
                channel_policy: dict) -> dict:
    """Escolhe uma hipótese inédita e delega trabalhos. Nunca gera nem publica."""
    if snapshot.get("history_complete") is not True:
        raise DuplicateTopic("BLOQUEADO_SEM_HISTORICO_COMPLETO")
    if (snapshot.get("channel_id") != channel_policy.get("youtube_channel_id")
            or snapshot.get("channel_id") != reservations.get("channel_id")):
        raise DuplicateTopic("IDENTIDADE_DO_CANAL_DIVERGENTE")
    perf = analyse_performance(snapshot)
    if perf["confidence"] == "insufficient_data":
        return {"schema": "videoforge/channel-idea/v1", "status": "insufficient_metrics",
                "channel_id": snapshot["channel_id"], "candidates_approved": 0,
                "metrics": perf, "selected": None, "production_enabled": False}
    paused = {norm(name) for name in channel_policy.get("paused_animes", [])}
    allowed = []
    rejected = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            rejected.append({"reason": "candidate_invalid"})
            continue
        if norm(candidate.get("anime", "")) in paused:
            rejected.append({"reason": "anime_paused"})
            continue
        if not candidate.get("evidence", {}).get("source"):
            rejected.append({"reason": "source_missing"})
            continue
        try:
            assert_unique(candidate, inventory=snapshot, reservations=reservations)
        except DuplicateTopic as exc:
            rejected.append({"reason": str(exc)})
            continue
        # O gênero, ângulo e anime dependem de classificação editorial, não
        # são inferidos como fatos de um título externo ou ranking arbitrário.
        genre = norm(candidate.get("genero", ""))
        proposal_format = norm(candidate.get("formato", ""))
        if genre not in {"curiosidade", "teoria", "analise", "comparativo", "noticias", "historia"}:
            rejected.append({"reason": "genre_invalid"})
            continue
        length = candidate.get("duracao_segundos")
        if not isinstance(length, int) or not 30 <= length <= 3600:
            rejected.append({"reason": "duration_invalid"})
            continue
        # A adequação de duração usa somente medianas de grupos com >= 3 amostras.
        match = duration_bucket(length) == perf["best_duration_bucket"]
        fit = (2 if match else 0) if perf["best_duration_bucket"] else 0
        source_signal = candidate["evidence"].get("strength", "unknown")
        # Um hype externo é hipótese, não prova de performance do canal.
        credibility = 1 if source_signal == "documented" else 0
        allowed.append((fit + credibility,
                        editorial_fingerprint(candidate), candidate))
    allowed.sort(key=lambda item: (-item[0], item[1]))
    if not allowed:
        return {"schema": "videoforge/channel-idea/v1", "status": "no_unique_candidate",
                "channel_id": snapshot["channel_id"], "candidates_approved": 0,
                "rejections": rejected, "metrics": perf, "selected": None,
                "production_enabled": False}
    selected = dict(allowed[0][2])
    return {
        "schema": "videoforge/channel-idea/v1",
        "status": "proposed_for_review",
        "channel_id": snapshot["channel_id"],
        "manager_id": "gerente-canal-" + channel_policy["id"],
        "selected": selected,
        "evidence": {
            "youtube_window": snapshot.get("window"),
            "duration_rationale": perf,
            "source": selected.get("evidence"),
            "novelty": "heuristic_precheck_only_requires_editorial_review",
        },
        "candidates_approved": len(allowed),
        "rejections": rejected,
        "requires_reservation": True, "requires_editorial_review": True,
        "production_enabled": False, "upload_enabled": False,
    }
