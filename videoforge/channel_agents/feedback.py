"""Medição após publicar: compara pares e seleciona UM experimento editorial.

Todas as métricas vêm de uma janela comparável do mesmo canal. Não infere
causalidade e não usa visualizações brutas de Shorts como sinônimo de engajadas.
Não produz vídeos, não envia uploads nem gera custos.
"""
from __future__ import annotations

from statistics import median
from .strategy import _performance


def _non_negative(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    if 0 <= result < 10**12:
        return result
    return None


def evaluate_uploaded_video(snapshot: dict, *, video_id: str,
                            detailed_insights: dict | None = None) -> dict:
    """Avalia evidência observada. Uma hipótese experimental por avaliação."""
    if (snapshot.get("schema") != "videoforge/channel-research/v1"
            or snapshot.get("history_complete") is not True
            or snapshot.get("count") != len(snapshot.get("videos", []))
            or not snapshot.get("channel_id")):
        raise ValueError("Histórico YouTube incompleto")
    matches = [v for v in snapshot["videos"] if v.get("id") == video_id]
    if len(matches) != 1:
        raise ValueError("Vídeo não pertence ao canal autenticado")
    target = matches[0]
    result = _performance(target)
    if not result:
        return {"status": "insufficient_data", "video_id": video_id,
                "next_experiment": None, "causal_claim": False}
    video_format = target.get("format")  # anotação editorial, não inferida pela duração
    peers = []
    for row in snapshot["videos"]:
        if row.get("id") == video_id:
            continue
        perf = _performance(row)
        if perf and perf["duration_bucket"] == result["duration_bucket"]:
            if video_format is not None and row.get("format") != video_format:
                continue
            peers.append((row, perf))
    if len(peers) < 3:
        return {"status": "insufficient_peers", "video_id": video_id,
                "next_experiment": None, "causal_claim": False}

    # Shorts: não comparar a nova contagem de starts com visualizações
    # engajadas, especialmente nos períodos em que a definição mudou.
    basis = "engagedViews" if video_format == "short" else "views"
    measured = result["views"] if basis == "views" else _non_negative(
        (target.get("metrics") or {}).get("engagedViews"))
    peer_values = ([p["views"] for _, p in peers] if basis == "views" else [
        _non_negative((row.get("metrics") or {}).get("engagedViews")) for row, _ in peers])
    if measured is None or any(x is None for x in peer_values):
        return {"status": "insufficient_engaged_views", "video_id": video_id,
                "metric_basis": basis, "next_experiment": None, "causal_claim": False}

    baseline_views = median(peer_values)
    baseline_retention = median(p["retention"] for _, p in peers)
    relative_views = measured / max(1, baseline_views)
    retention_delta_pct = 100 * (result["retention"] - baseline_retention)
    early_drop = None
    insights_count = None
    if detailed_insights is not None:
        if (detailed_insights.get("schema") != "videoforge/video-insights/v1"
                or detailed_insights.get("channel_id") != snapshot["channel_id"]
                or detailed_insights.get("video_id") != video_id
                or detailed_insights.get("window") != {
                    "start": snapshot.get("window", {}).get("start"),
                    "end": snapshot.get("window", {}).get("end"),
                } or detailed_insights.get("read_only") is not True):
            raise ValueError("Detalhes de retenção não correspondem ao canal/janela")
        drop = detailed_insights.get("largest_adjacent_retention_drop")
        if isinstance(drop, dict):
            try:
                at = float(drop.get("from_ratio"))
                amount = float(drop.get("drop"))
            except (TypeError, ValueError):
                raise ValueError("Queda de retenção inválida") from None
            if not 0 <= at <= 1 or not -20 <= amount <= 20:
                raise ValueError("Queda de retenção fora de limites")
            if at <= .2 and amount >= .12:
                early_drop = round(amount, 3)
        insights_count = len(detailed_insights.get("retention_points") or [])

    if early_drop is not None:
        action = "test_first_20_percent_hook"
    elif relative_views >= 1.15 and retention_delta_pct >= 0:
        action = "test_new_original_angle"
    else:
        action = "test_pacing_and_story_structure"

    subscribers = _non_negative((target.get("metrics") or {}).get("subscribersGained"))
    conversion = round(1000 * subscribers / measured, 2) if subscribers is not None and measured > 0 else None
    return {
        "schema": "videoforge/channel-experiment-feedback/v1",
        "status": "observed", "video_id": video_id,
        "channel_id": snapshot["channel_id"],
        "window": snapshot.get("window"),
        "content_format": video_format or "unknown",
        "metric_basis": basis, "peer_samples": len(peers),
        "relative_views_to_peer_median": round(relative_views, 3),
        "retention_delta_percentage_points": round(retention_delta_pct, 2),
        "subscribers_per_1000_measured_views": conversion,
        "largest_early_retention_drop": early_drop,
        "detailed_retention_samples": insights_count,
        "next_experiment": action,
        "experiment_variables": 1,
        "review_before_production": True,
        "causal_claim": False, "no_repeat_topic": True,
        "publication_enabled": False,
        "note": "Observação não causal. Nunca repetir tema/abordagem. Autorizar e medir UMA alteração por teste.",
    }
