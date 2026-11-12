"""Modelo de revisão por vídeo para a etapa de QA (somente planejamento).

Campos de notas são pendentes, nunca preenche scores fictícios.
O documento público NÃO pode ser submetido como evidência confiável.
"""
from __future__ import annotations

from .quality_gate import load_policy


def review_template(plan: dict) -> dict:
    if not isinstance(plan, dict) or plan.get("schema") != "videoforge/production-delegation/v1":
        raise ValueError("Plano de produção incompatível")
    policy = load_policy()
    channel = plan["demand"]["canal"]
    checks = policy["required_checks"] + (policy["kids_required_checks"] if channel == "manu-kids" else [])
    return {
        "schema": "videoforge/quality-evidence/v1",
        "source": "unverified_template_only",
        "job_id": plan["demand"]["id"], "channel": channel,
        "format": None, "attempt": None, "media_sha256": None,
        "producer_ids": [], "reviewers": {"content":"revisor-conteudo","technical":"qa-tecnico"},
        "scores": {
            key: {"score": None, "reviewer_id": cfg["reviewer"], "reason": ""}
            for key,cfg in policy["dimensions"].items()
        },
        "checks": {key: None for key in checks},
        "local_quality_policy": {
            "minimum_score": policy["minimum_weighted_score"],
            "maximum_revisions": policy["max_revisions"],
            "review_before_publish": True,
            "automatic_publication": False,
        },
        "status": "awaiting_real_media_and_independent_qa",
        "note": "Preenchido somente por revisores confiáveis no backend, com hash real de MP4 e ffprobe. O modelo não é aprovação.",
    }
