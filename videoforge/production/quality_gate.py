"""Portão de qualidade antes da aprovação — SEM gerar, enviar ou avaliar IA por conta própria.

As notas são avaliações editoriais de revisores INDEPENDENTES no backend,
não uma pontuação do YouTube. Evidência de upload nunca autoriza publicação.
Política definida em config/quality-policy.json.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from subprocess import run, TimeoutExpired
import json
import re

ROOT = Path(__file__).resolve().parents[2]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{3,80}$")
MAX_FILE_BYTES = 2 * 1024 * 1024 * 1024


class QualityEvidenceError(ValueError):
    """Evidência inválida: avaliação bloqueada sem executar produção."""


def load_policy(root: Path = ROOT) -> dict:
    policy = json.loads((Path(root) / "config/quality-policy.json").read_text(encoding="utf-8"))
    if policy.get("schema") != "videoforge/quality-policy/v1":
        raise QualityEvidenceError("QUALITY_POLICY_SCHEMA_INVALID")
    dimensions = policy.get("dimensions")
    if not isinstance(dimensions, dict) or len(dimensions) < 6:
        raise QualityEvidenceError("QUALITY_POLICY_DIMENSIONS_INVALID")
    if abs(sum(x.get("weight", -1) for x in dimensions.values()) - 1) > 0.000001:
        raise QualityEvidenceError("QUALITY_POLICY_WEIGHTS_INVALID")
    for spec in dimensions.values():
        if (spec.get("reviewer") not in {"revisor-conteudo", "qa-tecnico"}
                or not isinstance(spec.get("min_score"), int)
                or not 0 <= spec["min_score"] <= 100):
            raise QualityEvidenceError("QUALITY_POLICY_REVIEWER_OR_SCORE_INVALID")
    if policy.get("publication", {}).get("auto_publish_enabled") is not False:
        raise QualityEvidenceError("QUALITY_POLICY_MUST_DISABLE_AUTO_PUBLISH")
    return policy


def inspect_media(video: Path, *, runner=run) -> dict:
    """Lê MP4 de disco com ffprobe, sem interpretar informações declaradas pela IA."""
    video = Path(video)
    if video.is_symlink() or not video.is_file() or video.suffix.lower() != ".mp4":
        raise QualityEvidenceError("VIDEO_FILE_MISSING_OR_UNSAFE")
    size = video.stat().st_size
    if size < 1024 or size > MAX_FILE_BYTES:
        raise QualityEvidenceError("VIDEO_FILE_SIZE_INVALID")
    h = sha256()
    with video.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    try:
        result = runner(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration,format_name:stream=codec_type,codec_name,width,height,avg_frame_rate",
             "-of", "json", str(video)],
            text=True, capture_output=True, timeout=20, check=False,
        )
    except (FileNotFoundError, TimeoutExpired, OSError):
        raise QualityEvidenceError("FFPROBE_UNAVAILABLE_OR_TIMEOUT") from None
    if result.returncode != 0 or len(result.stdout) > 2_000_000:
        raise QualityEvidenceError("FFPROBE_VIDEO_INVALID")
    try:
        parsed = json.loads(result.stdout)
        fmt = parsed["format"]
        duration = float(fmt["duration"])
        if not 0 < duration < 7201 or "mp4" not in fmt.get("format_name", ""):
            raise ValueError()
        tracks = parsed["streams"]
        videos = [s for s in tracks if s.get("codec_type") == "video"]
        audios = [s for s in tracks if s.get("codec_type") == "audio"]
        if len(videos) != 1 or not audios:
            raise ValueError()
        stream = videos[0]
        width, height = int(stream["width"]), int(stream["height"])
        fps = float(Fraction(stream["avg_frame_rate"]))
        if not stream.get("codec_name") or not audios[0].get("codec_name"):
            raise ValueError()
        if not 1 <= width <= 8192 or not 1 <= height <= 8192 or not 0 < fps <= 240:
            raise ValueError()
    except (KeyError, ValueError, TypeError, ZeroDivisionError, OverflowError):
        raise QualityEvidenceError("VIDEO_MEDIA_STREAMS_INVALID") from None
    return {"sha256": h.hexdigest(), "bytes": size,
            "duration_seconds": round(duration, 3),
            "width": width, "height": height, "fps": round(fps, 3),
            "audio_stream_present": True, "video_stream_present": True,
            "source": "local_ffprobe_and_sha256"}


def evaluate_quality(report: dict, *, media_path: Path,
                     job_id: str, channel: str,
                     expected_duration_seconds: int,
                     root: Path = ROOT, trusted_backend: bool = False,
                     probe=inspect_media) -> dict:
    """Aprova somente para REVISÃO HUMANA. Nunca para upload direto.

    trusted_backend só pode ser passado pelo executor privado verificado, não
    por um browser/relatório público. probe é injetável para testes unitários;
    produção usa inspect_media real por padrão.
    """
    policy = load_policy(root)
    if not trusted_backend or not isinstance(report, dict) or report.get("source") != "trusted_backend_qa":
        raise QualityEvidenceError("QUALITY_UNTRUSTED_EVIDENCE")
    if report.get("schema") != "videoforge/quality-evidence/v1":
        raise QualityEvidenceError("QUALITY_EVIDENCE_SCHEMA_INVALID")
    if (not isinstance(job_id, str) or not SAFE_ID.fullmatch(job_id)
            or report.get("job_id") != job_id or report.get("channel") != channel
            or channel not in {"otaku-br", "otaku-en", "gamer", "manu-kids", "alchemy-lab"}):
        raise QualityEvidenceError("QUALITY_JOB_OR_CHANNEL_MISMATCH")
    if (not isinstance(expected_duration_seconds, int)
            or isinstance(expected_duration_seconds, bool)
            or not 5 <= expected_duration_seconds <= 7200):
        raise QualityEvidenceError("QUALITY_DURATION_INVALID")
    attempt = report.get("attempt")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or not 1 <= attempt <= policy["max_revisions"] + 1:
        raise QualityEvidenceError("QUALITY_ATTEMPT_INVALID")
    producers = report.get("producer_ids")
    reviewers = report.get("reviewers")
    if (not isinstance(producers, list) or not producers
            or not all(isinstance(x, str) and SAFE_ID.fullmatch(x) for x in producers)
            or len(set(producers)) != len(producers)
            or not isinstance(reviewers, dict)
            or reviewers != {"content": "revisor-conteudo", "technical": "qa-tecnico"}
            or bool(set(producers) & set(reviewers.values()))):
        raise QualityEvidenceError("QUALITY_NOT_INDEPENDENTLY_REVIEWED")
    digest = report.get("media_sha256")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise QualityEvidenceError("QUALITY_MEDIA_HASH_INVALID")
    media = probe(Path(media_path))
    if digest != media["sha256"]:
        raise QualityEvidenceError("QUALITY_MEDIA_HASH_MISMATCH")
    # A mídia e a duração são verificadas antes da avaliação subjetiva.
    config = policy["media"]
    tolerance = max(config["duration_tolerance_seconds"],
                    expected_duration_seconds * config["duration_tolerance_ratio"])
    media_errors = []
    if abs(media["duration_seconds"] - expected_duration_seconds) > tolerance:
        media_errors.append("MEDIA_DURATION_MISMATCH")
    if min(media["width"], media["height"]) < config["min_dimension_px"]:
        media_errors.append("MEDIA_RESOLUTION_LOW")
    if not config["min_fps"] <= media["fps"] <= config["max_fps"]:
        media_errors.append("MEDIA_FPS_INVALID")
    if report.get("format") == "short" and media["duration_seconds"] < config["min_short_seconds"]:
        media_errors.append("SHORT_TOO_BRIEF_FOR_LOCAL_POLICY")

    grades = report.get("scores")
    if not isinstance(grades, dict) or set(grades) != set(policy["dimensions"]):
        raise QualityEvidenceError("QUALITY_SCORE_COVERAGE_INVALID")
    missing_threshold = []
    weighted = 0.0
    for key, spec in policy["dimensions"].items():
        grade = grades[key]
        if not isinstance(grade, dict):
            raise QualityEvidenceError("QUALITY_SCORE_INVALID")
        score = grade.get("score")
        reason = grade.get("reason")
        if (not isinstance(score, int) or isinstance(score, bool)
                or not 0 <= score <= 100
                or grade.get("reviewer_id") != spec["reviewer"]
                or not isinstance(reason, str) or not 12 <= len(reason.strip()) <= 400):
            raise QualityEvidenceError("QUALITY_SCORE_OR_REVIEWER_INVALID")
        weighted += score * spec["weight"]
        if score < spec["min_score"]:
            missing_threshold.append(key)
    checks = report.get("checks")
    expected_checks = set(policy["required_checks"])
    if channel == "manu-kids":
        expected_checks.update(policy["kids_required_checks"])
    if not isinstance(checks, dict) or not expected_checks <= set(checks):
        raise QualityEvidenceError("QUALITY_CHECKLIST_INCOMPLETE")
    if any(not isinstance(checks[name], bool) for name in expected_checks):
        raise QualityEvidenceError("QUALITY_CHECKLIST_NON_BOOLEAN")
    failing_checks = sorted(name for name in expected_checks if checks[name] is False)
    risk_checks = {
        "historico_e_reserva_verificados", "conteudo_original",
        "fatos_verificados", "direitos_revisados", "canal_correto",
        "divulgacao_ia_avaliada", "politica_infantil_verificada",
        "classificacao_publico_infantil_revisada",
    }
    critical = [name for name in failing_checks if name in risk_checks]
    failed = bool(missing_threshold or failing_checks or media_errors
                  or weighted < policy["minimum_weighted_score"])
    # Reprovação por direitos/originalidade não vira retry automático.
    if critical:
        decision = "blocked_policy"
    elif not failed:
        decision = "ready_for_human_approval"
    elif attempt > policy["max_revisions"]:
        decision = "suspended"
    else:
        decision = "rework"
    return {
        "schema": "videoforge/quality-decision/v1",
        "job_id": job_id, "channel": channel, "attempt": attempt,
        "status": decision, "weighted_score": round(weighted, 2),
        "score_threshold": policy["minimum_weighted_score"],
        "low_dimensions": sorted(missing_threshold),
        "failed_checks": failing_checks, "media_errors": media_errors,
        "next_step": {
            "ready_for_human_approval": "human_editorial_approval",
            "rework": "return_to_responsible_specialist",
            "suspended": "manager_diagnosis_and_human_review",
            "blocked_policy": "resolve_critical_policy_issue_before_new_attempt",
        }[decision],
        "remaining_revisions": max(0, policy["max_revisions"] - attempt + 1),
        "media_sha256": media["sha256"],
        "reviewers": reviewers,
        "youtube_score": None,
        "automatic_upload_authorized": False,
        "human_approval_required": True,
        "costly_regeneration_authorized": False,
    }
