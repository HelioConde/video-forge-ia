"""Avaliação pós-publicação com métricas equivalentes, sem declarar causalidade."""
from __future__ import annotations
from statistics import median
from .strategy import _performance, duration_bucket


def evaluate_uploaded_video(snapshot: dict, *, video_id: str) -> dict:
    """Compara vídeo a pares do MESMO canal e janela (não prevê viralização)."""
    if not snapshot.get("history_complete") or not snapshot.get("channel_id"):
        raise ValueError("Histórico YouTube incompleto")
    target = next((v for v in snapshot.get("videos", []) if v.get("id") == video_id), None)
    if target is None:
        raise ValueError("Vídeo não pertence ao canal autenticado")
    result = _performance(target)
    if not result:
        return {"status":"insufficient_data","video_id":video_id,
                "next_experiment": None, "causal_claim": False}
    peers = []
    for row in snapshot["videos"]:
        if row.get("id") == video_id:
            continue
        perf = _performance(row)
        if perf and perf["duration_bucket"] == result["duration_bucket"]:
            peers.append(perf)
    if len(peers) < 3:
        return {"status":"insufficient_peers","video_id":video_id,
                "next_experiment": None, "causal_claim": False}
    baseline_views = median(x["views"] for x in peers)
    baseline_retention = median(x["retention"] for x in peers)
    relative_views = result["views"] / max(1, baseline_views)
    retention_delta_pct = 100 * (result["retention"] - baseline_retention)
    # Alterar UMA variável editorial por teste: gancho, não recontar a pauta.
    action = ("test_new_original_angle" if relative_views >= 1.15
              and retention_delta_pct >= 0 else "test_hook_and_pacing")
    return {
        "schema": "videoforge/channel-experiment-feedback/v1",
        "status": "observed",
        "video_id": video_id,
        "channel_id": snapshot["channel_id"],
        "window": snapshot.get("window"),
        "peer_samples": len(peers),
        "relative_views_to_peer_median": round(relative_views, 3),
        "retention_delta_percentage_points": round(retention_delta_pct, 2),
        "next_experiment": action,
        "causal_claim": False,
        "no_repeat_topic": True,
        "note": "Correlação observada na janela, não efeito causal da IA. Usar tema novo.",
    }
