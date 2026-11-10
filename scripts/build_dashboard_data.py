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
    agents = [{
        "id": a["id"], "nome": text(a.get("nome")), "funcao": text(a.get("funcao")),
        "status": "nao_conectado",
        "tarefa": "Aguardando conexão com a produção real", "canal": None
    } for a in team]

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
                agent.update(updates[agent["id"]])

    return {
        "schema": "videoforge/agent-office/v1",
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fonte": "eventos_backend" if events else "apenas_configuracao",
        "tempo_real": False,
        "canais": channels, "agentes": agents,
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
