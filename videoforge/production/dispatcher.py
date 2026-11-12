"""Planejador determinístico de delegação de vídeos (SEM executar IA ou publicar).

Atribui entregas a especialistas lógicos, acompanha dependências e valida
aprovação humana. Não gera conteúdo nem cobra serviços.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
# (id, especialista, dependências, descrição da entrega)
STAGES = (
    ("briefing", "coordenador-pautas", (), "briefing.json"),
    ("pesquisa", "pesquisador", ("briefing",), "pesquisa.json"),
    ("roteiro", "roteirista-cenas", ("pesquisa",), "roteiro.json"),
    ("titulo", "titulo", ("roteiro",), "titulo.json"),
    ("descricao", "descricao", ("roteiro",), "descricao.md"),
    ("tags", "tags-seo", ("pesquisa", "roteiro"), "tags.json"),
    ("storyboard", "storyboard", ("roteiro",), "storyboard.json"),
    ("thumbnail", "thumbnail", ("roteiro",), "thumbnail.png"),
    ("narracao", "voz", ("roteiro",), "narracao.wav"),
    ("visuais", "ilustrador", ("storyboard",), "assets.json"),
    ("animacao", "animacao", ("visuais",), "animacoes.json"),
    ("legendas", "legendas", ("narracao", "roteiro"), "legendas.srt"),
    ("audio", "audio", ("narracao",), "audio-master.wav"),
    ("edicao", "montagem", ("animacao", "audio", "legendas"), "video.mp4"),
    ("qa_tecnico", "qa-tecnico", ("edicao",), "qa-tecnico.json"),
    ("qa_conteudo", "revisor-conteudo", ("edicao", "titulo", "descricao", "tags", "thumbnail"), "qa-conteudo.json"),
    ("aprovacao", "gerente_geral", ("qa_tecnico", "qa_conteudo"), "aprovacao.json"),
    ("publicacao", "publicacao", ("aprovacao",), "publicacao.json"),
)


def build_plan(demand: dict[str, Any], *, root: Path = ROOT) -> dict:
    if not isinstance(demand, dict):
        raise ValueError("Demanda deve ser objeto.")
    required = {"id", "canal", "tema", "duracao_segundos"}
    if not required <= demand.keys():
        raise ValueError("Demanda exige id, canal, tema e duracao_segundos.")
    for name in ("id", "canal", "tema"):
        value = demand[name]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Campo obrigatório inválido: " + name)
    if not isinstance(demand["duracao_segundos"], int) or isinstance(demand["duracao_segundos"], bool) or not 5 <= demand["duracao_segundos"] <= 7200:
        raise ValueError("Duração fora dos limites.")
    if not demand["id"].replace("-", "").replace("_", "").isalnum() or len(demand["id"]) > 64:
        raise ValueError("Identificador de demanda inválido.")
    channels = {
        path.name for path in (root / "canal").iterdir()
        if path.is_dir() and (path / "canal.json").exists()
    }
    if demand["canal"] not in channels:
        raise ValueError("Canal desconhecido.")
    roster = json.loads((root / "agentes/equipe.json").read_text(encoding="utf-8"))
    specialists = {
        specialist["id"] for dept in roster["departamentos"]
        for specialist in dept["specialists"]
    }
    specialists.add("gerente_geral")
    jobs = []
    identifiers = set()
    for slug, worker, dependencies, filename in STAGES:
        if worker not in specialists:
            raise ValueError("Especialista ausente da equipe: " + worker)
        if not set(dependencies) <= identifiers:
            raise ValueError("Dependências incorretas para: " + slug)
        jobs.append({
            "id": slug,
            "responsavel": worker,
            "depende_de": list(dependencies),
            "entrega_esperada": filename,
            "status": "ready" if not dependencies else "blocked",
            "artifact_verified": False,
        })
        identifiers.add(slug)
    return {
        "schema": "videoforge/production-delegation/v1",
        "demand": {
            "id": demand["id"],
            "canal": demand["canal"],
            "tema": demand["tema"].strip()[:220],
            "duracao_segundos": demand["duracao_segundos"],
        },
        "mode": "planning_only",
        "execution_enabled": False,
        "publishing_enabled": False,
        "manager": "gerente_geral",
        "quality_gate": {"status": "not_evaluated", "required": True,
                         "max_revisions": 2, "human_approval_required": True},
        "tasks": jobs,
    }


def ready_tasks(plan: dict) -> list[str]:
    gate = plan.get("quality_gate", {})
    if gate.get("status") in ("suspended", "blocked_policy"):
        return []  # gerente precisa resolver antes de consumir novos recursos
    done = {t["id"] for t in plan["tasks"] if t["status"] == "done" and t.get("artifact_verified") is True}
    return [
        t["id"] for t in plan["tasks"] if
        t["status"] in ("ready", "blocked") and
        (t["id"] != "aprovacao" or gate.get("status") == "ready_for_human_approval") and
        set(t["depende_de"]) <= done
    ]


def mark_verified(plan: dict, task_id: str, *, evidence_path: Path) -> None:
    if task_id == "publicacao":
        raise ValueError("O planejador não autoriza publicações.")
    matches = [t for t in plan["tasks"] if t["id"] == task_id]
    if len(matches) != 1 or task_id not in ready_tasks(plan):
        raise ValueError("Tarefa desconhecida ou com dependências pendentes.")
    if not evidence_path.is_file() or evidence_path.stat().st_size == 0:
        raise ValueError("Entrega verificável não encontrada.")
    matches[0]["status"] = "done"
    matches[0]["artifact_verified"] = True


def attach_quality_report(plan: dict, report: dict, *, media_path: Path,
                          trusted_backend: bool = False, probe=None) -> dict:
    """Portão de QA final; não executa IA, renderização ou uploads.

    Chamadas devem vir do executor privado que comprova os revisores. A
    evidência do frontend ou arquivo público jamais deve ser confiada.
    """
    from .quality_gate import evaluate_quality, inspect_media
    if plan.get("schema") != "videoforge/production-delegation/v1":
        raise ValueError("Plano incompatível")
    previous_gate = plan.get("quality_gate", {})
    if previous_gate.get("status") in (
        "suspended", "blocked_policy", "ready_for_human_approval"
    ):
        raise ValueError("QA finalizado ou suspenso: reabertura exige gerente humano")
    previous_attempt = previous_gate.get("attempt", 0)
    if (not isinstance(previous_attempt, int) or
            report.get("attempt") != previous_attempt + 1):
        raise ValueError("Tentativas de revisão devem aumentar sequencialmente")
    by_id = {t["id"]: t for t in plan["tasks"]}
    for qa_id in ("qa_tecnico", "qa_conteudo"):
        qa = by_id.get(qa_id, {})
        if qa.get("status") != "done" or qa.get("artifact_verified") is not True:
            raise ValueError("Revisões técnicas e editoriais ainda não verificadas")
    if by_id["aprovacao"]["status"] == "done":
        raise ValueError("QA não pode ser alterado depois da aprovação")
    kwargs = {}
    if probe is not None:
        kwargs["probe"] = probe  # injeção somente para testes privados
    result = evaluate_quality(
        report, media_path=media_path, trusted_backend=trusted_backend,
        job_id=plan["demand"]["id"], channel=plan["demand"]["canal"],
        expected_duration_seconds=plan["demand"]["duracao_segundos"],
        **kwargs,
    )
    plan["quality_gate"] = result
    if result["status"] == "rework":
        # Qualquer melhoria em uma entrega invalida suas dependentes
        # (incluindo QA); não reutilizar uma aprovação de versão anterior.
        targets = set()
        mapping = {
            "originalidade": "pesquisa", "pesquisa_e_fatos": "pesquisa",
            "roteiro_e_gancho": "roteiro", "narracao": "narracao",
            "consistencia_visual": "visuais", "edicao_e_ritmo": "edicao",
            "titulo_e_thumbnail": "titulo", "qualidade_tecnica": "edicao",
        }
        targets.update(mapping[k] for k in result["low_dimensions"])
        if result["failed_checks"] or result["media_errors"] or not targets:
            targets.add("edicao")
        changed = True
        while changed:
            previous = len(targets)
            targets.update(t["id"] for t in plan["tasks"]
                           if any(dep in targets for dep in t["depende_de"]))
            changed = len(targets) != previous
        for task in plan["tasks"]:
            if task["id"] in targets:
                task["status"] = "blocked"
                task["artifact_verified"] = False
        plan["quality_gate"]["rework_targets"] = sorted(targets)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Planejamento sem IA de produtora")
    parser.add_argument("--demand", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("output/delegacao.json"))
    args = parser.parse_args()
    data = json.loads(args.demand.read_text(encoding="utf-8"))
    result = build_plan(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"DELEGACAO_PRONTA: {len(result['tasks'])} tarefas, {len(ready_tasks(result))} liberada(s); sem geração ou publicação")


if __name__ == "__main__":
    main()
