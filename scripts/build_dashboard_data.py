"""Exporta somente estados seguros para um painel público GitHub Pages."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATES = {"nao_conectado", "aguardando", "trabalhando", "revisao", "concluido", "erro"}


def text(value: object, limit: int = 100) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def make_snapshot(root: Path = ROOT, events: Path | None = None) -> dict:
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

    return {
        "schema": "videoforge/agent-office/v1",
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fonte": "eventos_backend" if events else "apenas_configuracao",
        "tempo_real": False,
        "canais": channels, "agentes": agents, "organizacao": organization,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "site/data/status.json")
    args = parser.parse_args()
    snapshot = make_snapshot(events=args.events)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Painel preparado: {len(snapshot['canais'])} canais; {len(snapshot['agentes'])} agentes (sem execução de IA)")


if __name__ == "__main__":
    main()
