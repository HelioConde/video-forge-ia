"""Subgerente: avaliação baseada em entregas comprovadas, sem IA ou créditos.

Nenhum funcionário recebe pontos por só existir. A média é por trabalho,
e NÃO soma tarefas: evita premiar volume, uploads artificiais ou retrabalho.
Evidência só deve ser fornecida por executor backend confiável, nunca pelo
formulário público ou declaração do próprio agente avaliado.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from hashlib import sha256
from pathlib import Path
import json
import re
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
SHA256 = re.compile(r"^[a-f0-9]{64}$")
TASK_ID = re.compile(r"^[a-zA-Z0-9_-]{3,80}$")
INDEPENDENT_QA = frozenset({
    "revisor", "revisor-conteudo", "revisor-narrativa",
    "revisor-visual", "qa-tecnico",
})
MIN_TASKS = 3


class RankingEvidenceError(ValueError):
    """Evidência ausente, inconsistente ou autoclassificada."""


def _catalog(root: Path) -> dict[str, dict]:
    roster = json.loads((root / "agentes/equipe.json").read_text(encoding="utf-8"))
    channels = json.loads((root / "agentes/gerentes-canais.json").read_text(encoding="utf-8"))
    employees: dict[str, dict] = {}

    def add(employee_id, name, cohort, role):
        if not isinstance(employee_id, str) or not employee_id or employee_id in employees:
            raise RankingEvidenceError("EMPLOYEE_DUPLICATE_OR_INVALID")
        employees[employee_id] = {
            "employee_id": employee_id, "name": name,
            "cohort": cohort, "role": role,
        }

    for agent in roster["agentes"]:
        if agent["id"] != "subgerente":
            add(agent["id"], agent["nome"], "visual", agent["funcao"])
    for dept in roster["departamentos"]:
        for worker in dept["specialists"]:
            add(worker["id"], worker["nome"], "especialistas", worker["funcao"])
    for mgr in channels["channel_managers"]:
        add(mgr["id"], mgr["name"], "gerentes", "Estratégia do canal " + mgr["channel"])
    if "subgerente" not in {x["id"] for x in roster["agentes"]}:
        raise RankingEvidenceError("SUBGERENTE_NOT_REGISTERED")
    return employees


def _as_date(value, name):
    try:
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError()
        return date.fromisoformat(value)
    except ValueError:
        raise RankingEvidenceError(name + "_INVALID") from None


def _sha(value):
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _validate_record(event: dict, *, workers: dict, channels: set[str],
                     start: date, end: date, seen: set) -> None:
    if not isinstance(event, dict):
        raise RankingEvidenceError("EVIDENCE_NOT_OBJECT")
    employee = event.get("employee_id")
    reviewer = event.get("reviewer_id")
    if employee not in workers or reviewer not in INDEPENDENT_QA or reviewer == employee:
        raise RankingEvidenceError("WORKER_OR_INDEPENDENT_REVIEW_INVALID")
    job = event.get("job_id")
    task = event.get("task_id")
    channel = event.get("channel")
    when = _as_date(event.get("completed_date"), "COMPLETION_DATE")
    if (not isinstance(job, str) or not TASK_ID.fullmatch(job)
            or not isinstance(task, str) or not TASK_ID.fullmatch(task)
            or channel not in channels
            or not (start <= when <= end)):
        raise RankingEvidenceError("WORK_SCOPE_OR_PERIOD_INVALID")
    # Um trabalho tem apenas um beneficiário. O mesmo job não gera
    # 10 pontuações porque o agente submeteu dez versões da entrega.
    if job in seen:
        raise RankingEvidenceError("JOB_EVIDENCE_DUPLICATED")
    seen.add(job)
    if event.get("result") != "qa_approved" or not _sha(event.get("artifact_sha256")):
        raise RankingEvidenceError("UNVERIFIED_ARTIFACT_OR_QA")
    quality = event.get("quality")
    attempts = event.get("attempts")
    if not isinstance(quality, int) or isinstance(quality, bool) or not 0 <= quality <= 100:
        raise RankingEvidenceError("QA_QUALITY_INVALID")
    if not isinstance(attempts, int) or isinstance(attempts, bool) or not 1 <= attempts <= 10:
        raise RankingEvidenceError("QA_ATTEMPTS_INVALID")
    if event.get("policy_compliant") is not True:
        raise RankingEvidenceError("COMPLIANCE_NOT_APPROVED")
    if not isinstance(event.get("collaboration_confirmed"), bool):
        raise RankingEvidenceError("COLLABORATION_INVALID")
    improved = event.get("improvement")
    if improved is not None:
        if not isinstance(improved, dict) or set(improved) != {
            "previous_artifact_sha256", "previous_quality",
            "summary", "reviewed_by"
        }:
            raise RankingEvidenceError("IMPROVEMENT_EVIDENCE_INVALID")
        previous_quality = improved["previous_quality"]
        if (not isinstance(previous_quality, int) or isinstance(previous_quality, bool)
                or not 0 <= previous_quality <= 100
                or quality < previous_quality + 5
                or not _sha(improved["previous_artifact_sha256"])
                or improved["previous_artifact_sha256"] == event["artifact_sha256"]
                or improved["reviewed_by"] not in INDEPENDENT_QA
                or improved["reviewed_by"] == employee
                or not isinstance(improved["summary"], str)
                or not 15 <= len(improved["summary"].strip()) <= 280):
            raise RankingEvidenceError("IMPROVEMENT_NOT_VERIFIED")


def _score(event: dict) -> dict:
    # 50 qualidade, 15 consistência da primeira entrega, 10 colaboração,
    # 20 melhoria validada e 5 conformidade; nunca premiar número de uploads.
    quality = round(event["quality"] * .5)
    reliability = 15 if event["attempts"] == 1 else 9 if event["attempts"] == 2 else 4
    collaboration = 10 if event["collaboration_confirmed"] else 0
    learning = 20 if event.get("improvement") is not None else 0
    compliance = 5  # evento já passou na revisão de regras
    return {
        "qualidade": quality, "consistencia": reliability,
        "colaboracao": collaboration, "evolucao": learning,
        "conformidade": compliance, "total": quality+reliability+collaboration+learning+compliance,
    }


def _suggestions(events: list[dict]) -> list[str]:
    notes = []
    average = mean(x["quality"] for x in events)
    if average < 80:
        notes.append("Priorizar checklist de qualidade e revisão antes de entregar.")
    if mean(x["attempts"] for x in events) > 1.3:
        notes.append("Estudar as causas das revisões e reduzir erros já conhecidos.")
    if mean(int(x["collaboration_confirmed"]) for x in events) < .6:
        notes.append("Documentar decisões e melhorar a passagem de contexto entre especialistas.")
    if not any(x.get("improvement") for x in events):
        notes.append("Propor uma melhoria concreta e validar seu efeito em uma nova entrega.")
    if not notes:
        notes.append("Compartilhar práticas que deram certo e testar uma melhoria nova.")
    return notes[:3]


def rank_employees(evidence: dict, *, root: Path = ROOT) -> dict:
    """Ranqueia funções de IA; não inclui desempenho de pessoas reais."""
    if not isinstance(evidence, dict) or evidence.get("schema") != "videoforge/performance-evidence/v1":
        raise RankingEvidenceError("PERFORMANCE_SCHEMA_INVALID")
    period = evidence.get("period")
    if not isinstance(period, dict):
        raise RankingEvidenceError("PERIOD_MISSING")
    start = _as_date(period.get("start"), "PERIOD_START")
    end = _as_date(period.get("end"), "PERIOD_END")
    if end < start or (end-start).days > 92:
        raise RankingEvidenceError("PERIOD_OUT_OF_RANGE")
    if evidence.get("source") != "trusted_backend_qa":
        raise RankingEvidenceError("UNTRUSTED_EVIDENCE_SOURCE")
    rows = evidence.get("events")
    if not isinstance(rows, list) or len(rows) > 10000:
        raise RankingEvidenceError("INVALID_EVENT_COUNT")
    workers = _catalog(root)
    channels = {p.name for p in (root / "canal").iterdir()
                if p.is_dir() and (p / "canal.json").is_file()}
    by_worker = defaultdict(list)
    seen = set()
    for row in rows:
        _validate_record(row, workers=workers, channels=channels,
                         start=start, end=end, seen=seen)
        by_worker[row["employee_id"]].append(row)

    ranked = []
    waiting = []
    for worker_id, meta in workers.items():
        reviewed = by_worker.get(worker_id, [])
        if len(reviewed) < MIN_TASKS:
            waiting.append({**meta, "status": "amostra_insuficiente",
                            "verified_tasks": len(reviewed), "points": None})
            continue
        scores = [_score(entry) for entry in reviewed]
        points = round(mean(s["total"] for s in scores), 1)
        ranked.append({
            **meta, "status": "avaliado", "points": points,
            "verified_tasks": len(reviewed),
            "score_components": {
                key: round(mean(s[key] for s in scores), 1)
                for key in ("qualidade","consistencia","colaboracao","evolucao","conformidade")
            },
            "quality_mean": round(mean(x["quality"] for x in reviewed), 1),
            "improvement_actions": _suggestions(reviewed),
        })
    ranked.sort(key=lambda x: (-x["points"], -x["quality_mean"], x["employee_id"]))
    for idx, item in enumerate(ranked, 1):
        item["rank"] = idx
        item["cohort_rank"] = 1 + sum(x["cohort"] == item["cohort"] for x in ranked[:idx-1])
    return {
        "schema": "videoforge/submanager-ranking/v1",
        "manager_id": "subgerente",
        "period": {"start":start.isoformat(),"end":end.isoformat()},
        "status": "ready" if ranked else "awaiting_verified_evidence",
        "basis": "only independently_qa_approved_artifacts",
        "min_tasks": MIN_TASKS,
        "max_points_per_task": 100,
        "points_do_not_authorize_publication": True,
        "auto_modify_agents": False,
        "total_verified_jobs": len(seen),
        "ranking": ranked,
        "unrated": waiting,
    }
