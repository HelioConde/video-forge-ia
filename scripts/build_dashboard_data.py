"""Exporta somente estados seguros para um painel público GitHub Pages."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from datetime import timedelta
import sys

ROOT = Path(__file__).resolve().parents[1]
# Compatível tanto com 'python scripts/build_dashboard_data.py' (Pages)
# quanto com import do módulo nos testes.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from videoforge.production.subgerente import rank_employees
STATES = {"nao_conectado", "aguardando", "trabalhando", "revisao", "concluido", "erro"}


def text(value: object, limit: int = 100) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def make_snapshot(root: Path = ROOT, events: Path | None = None,
                  performance_evidence: Path | None = None) -> dict:
    channels = []
    for folder in sorted((root / "canal").iterdir()):
        if not folder.is_dir():
            continue
        config = json.loads((folder / "canal.json").read_text(encoding="utf-8"))
        if config["id"] != folder.name:
            raise ValueError("Pasta e ID de canal diferentes")
        channels.append({
            "id": folder.name,
            "nome": text(config.get("nome")),
            "idioma": text(config.get("idioma"), 12),
            "modelo": text(config.get("modelo_padrao"), 60),
        })

    # Cada canal tem UM gerente editorial próprio. A presença no cadastro
    # não significa autenticação com o YouTube ou trabalho real executado.
    registry = json.loads((root / "agentes/gerentes-canais.json").read_text(encoding="utf-8"))
    if registry.get("schema") != "videoforge/channel-managers/v1":
        raise ValueError("Registro de gerentes incompatível")
    manager_rows = registry.get("channel_managers")
    if not isinstance(manager_rows, list):
        raise ValueError("Registro de gerentes inválido")
    assigned = {}
    for mgr in manager_rows:
        if not isinstance(mgr, dict) or not mgr.get("channel") or mgr["channel"] in assigned:
            raise ValueError("Gerente repetido ou inválido")
        assigned[mgr["channel"]] = mgr
    if set(assigned) != {c["id"] for c in channels}:
        raise ValueError("Cada canal deve ter exatamente um gerente")
    for item in channels:
        mgr = assigned[item["id"]]
        youtube_config = json.loads(
            (root / "canal" / item["id"] / "canal.json").read_text(encoding="utf-8")
        ).get("youtube", {})
        if mgr.get("youtube_channel_id") != youtube_config.get("channel_id"):
            raise ValueError("Gerente vinculado a outro canal")
        item["gerente"] = {
            "id": text(mgr["id"], 75),
            "nome": text(mgr.get("name"), 90),
            "status": "nao_conectado",
            "funcao": "Pesquisa e estratégia editorial do próprio canal",
            "regra_antirrepeticao": True,
            "youtube_analytics": "nao_conectado",
        }

    roster = json.loads((root / "agentes/equipe.json").read_text(encoding="utf-8"))
    team = roster.get("agentes")
    if not isinstance(team, list) or not team:
        raise ValueError("Cadastro de agentes inválido")
    ids = [a["id"] for a in team]
    if len(ids) != len(set(ids)):
        raise ValueError("IDs duplicados de agente")
    # Diagnóstico seguro de integração, sem revelar modelos, tokens ou chaves.
    # "habilitado" apenas no cadastro NÃO significa agente IA em execução.
    known_ids = set(ids)
    for member in team:
        dependencies = member.get("depende_de", [])
        if (not isinstance(dependencies, list)
            or len(dependencies) != len(set(dependencies))
            or any(dep not in known_ids or dep == member["id"] for dep in dependencies)):
            raise ValueError("Dependências de agentes inválidas.")
    graph = {member["id"]: member["depende_de"] for member in team}
    visiting, visited = set(), set()
    def check_dependencies(aid: str) -> None:
        if aid in visiting:
            raise ValueError("Ciclo de dependências entre agentes.")
        if aid in visited:
            return
        visiting.add(aid)
        for dep in graph[aid]:
            check_dependencies(dep)
        visiting.remove(aid)
        visited.add(aid)
    for aid in ids:
        check_dependencies(aid)

    agents = []
    for member in team:
        enabled = member.get("habilitado") is True
        model_defined = isinstance(member.get("modelo_ia"), str) and bool(member["modelo_ia"].strip())
        blockers = []
        if not model_defined:
            blockers.append("Modelo de IA não definido")
        if not enabled:
            blockers.append("Executor desabilitado no cadastro")
        blockers.append("Sem telemetria de execução comprovada")
        agents.append({
            "id": member["id"], "nome": text(member.get("nome")),
            "funcao": text(member.get("funcao")), "status": "nao_conectado",
            "tarefa": "Aguardando conexão com a produção real", "canal": None,
            "conexao": {
                "modelo_definido": model_defined,
                "executor_habilitado": enabled,
                "eventos_observados": False,
                "dependencias": member["depende_de"],
                "pendencias": blockers,
            },
        })

    departments = roster.get("departamentos", [])
    if not isinstance(departments, list):
        raise ValueError("Departamentos inválidos.")
    organization = {
        "gerente": "Gerente geral (humano)",
        "modelo": "planejado_sem_ia",
        "especialistas_planejados": sum(
            len(dept.get("specialists", [])) for dept in departments
        ),
        "departamentos": [
            {
                "id": text(dept.get("id"), 40),
                "nome": text(dept.get("name"), 80),
                "lider": text(dept.get("lead"), 40),
                "especialistas_planejados": len(dept.get("specialists", [])),
            }
            for dept in departments
        ],
    }

    if events is not None:
        raw = json.loads(events.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("agents"), list):
            raise ValueError("Relatório de agentes inválido")
        known_agents = set(ids)
        known_channels = {row["id"] for row in channels}
        updates = {}
        for event in raw["agents"]:
            if not isinstance(event, dict) or event.get("id") not in known_agents:
                raise ValueError("ID de agente inválido")
            aid, status, canal = event["id"], event.get("status"), event.get("canal")
            if aid in updates or status not in STATES or (canal is not None and canal not in known_channels):
                raise ValueError("Evento de agente inconsistente")
            updates[aid] = {"status": status, "canal": canal, "tarefa": text(event.get("tarefa"))}
        for agent in agents:
            if agent["id"] in updates:
                update = updates[agent["id"]]
                # Um evento enviado por engano não liga uma IA desabilitada.
                if update["status"] in {"trabalhando", "revisao", "concluido"} and not (
                    agent["conexao"]["executor_habilitado"] and agent["conexao"]["modelo_definido"]
                ):
                    raise ValueError("Evento de execução para agente IA não configurado.")
                agent.update(update)
                if update["status"] != "nao_conectado":
                    agent["conexao"]["eventos_observados"] = True
                    agent["conexao"]["pendencias"] = [
                        x for x in agent["conexao"]["pendencias"]
                        if x != "Sem telemetria de execução comprovada"
                    ]

    # Ranking público traz somente nomes, pontos e melhorias, NUNCA hashes,
    # eventos por vídeo, revisões privadas ou métricas de canal.
    current = datetime.now(timezone.utc).date()
    ranking_input = (
        json.loads(performance_evidence.read_text(encoding="utf-8"))
        if performance_evidence is not None else {
            "schema": "videoforge/performance-evidence/v1",
            "source": "trusted_backend_qa",
            "period": {
                "start": (current - timedelta(days=29)).isoformat(),
                "end": current.isoformat(),
            },
            "events": [],
        }
    )
    ranking_raw = rank_employees(ranking_input, root=root)
    ranking_public = {
        "status": ranking_raw["status"],
        "manager_id": "subgerente",
        "min_tasks": ranking_raw["min_tasks"],
        "period": ranking_raw["period"],
        "total_verified_jobs": ranking_raw["total_verified_jobs"],
        "unrated_count": len(ranking_raw["unrated"]),
        "ranking": [
            {
                "id": row["employee_id"], "name": text(row["name"]),
                "rank": row["rank"], "points": row["points"],
                "verified_tasks": row["verified_tasks"],
                "cohort": row["cohort"],
                "improvements": [text(note, 180)
                                  for note in row["improvement_actions"]],
            } for row in ranking_raw["ranking"]
        ],
        "evidence_connected": performance_evidence is not None,
    }

    return {
        "schema": "videoforge/agent-office/v1",
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fonte": "eventos_backend" if events else "apenas_configuracao",
        "tempo_real": False,
        "canais": channels, "agentes": agents, "organizacao": organization,
        "ranking_funcionarios": ranking_public,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path)
    parser.add_argument("--performance-evidence", type=Path,
                        help="Evidência QA privada do backend confiável (somente entrada local)")
    parser.add_argument("--output", type=Path, default=ROOT / "site/data/status.json")
    args = parser.parse_args()
    snapshot = make_snapshot(events=args.events, performance_evidence=args.performance_evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Painel preparado: {len(snapshot['canais'])} canais; {len(snapshot['agentes'])} agentes (sem execução de IA)")


if __name__ == "__main__":
    main()
