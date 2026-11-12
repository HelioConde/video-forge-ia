"""Um gerente por canal; especialistas compartilhados, trabalhos isolados.

Plano = sugestão auditável, sem conexão com Proxy e sem publicar/consumir IA.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from videoforge.production.dispatcher import build_plan
from videoforge.proxy.roles import plan_bindings
from .strategy import select_idea
from .youtube import oauth_access_token, YouTubeReadOnly, YouTubeReadError

ROOT = Path(__file__).resolve().parents[2]

ROLE_INSTRUCTIONS = {
    "briefing": "Documentar objetivo do gerente, público, anime, assunto, gênero, ângulo e fontes verificáveis",
    "pesquisa": "Verificar fatos de fontes primárias e registrar afirmações, datas, spoilers e direitos; sem copiar outros vídeos",
    "roteiro": "Criar gancho específico e texto narrativo original, com ritmo proporcional à duração e sem afirmações inventadas",
    "titulo": "Propor título fiel ao roteiro aprovado, sem clickbait enganoso; verificar antirrepetição de título",
    "descricao": "Escrever descrição fiel ao roteiro e fontes; contextualizar direitos e conteúdo sintético quando aplicável",
    "tags": "Selecionar tags relevantes, sem repetir metadados internos ou de outro canal",
    "storyboard": "Planejar cada cena e provas do que será narrado, evitando reutilização de cenas de outra produção",
    "thumbnail": "Criar thumbnail original coerente com o roteiro e as regras de direitos",
    "narracao": "Entregar texto para locução e áudio apropriado à duração, ritmo, idioma e gênero do canal",
    "visuais": "Produzir imagens originais com consistência de personagens e sem imitar material oficial",
    "animacao": "Planejar movimentos e temporizações conforme storyboard, sem simular assets ausentes",
    "legendas": "Sincronizar legendas com a narração final",
    "audio": "Mixar voz e efeitos adequados sem prejudicar compreensão",
    "edicao": "Montar vídeo e adaptar cortes/ritmo à retenção observada na janela de Analytics",
    "qa_tecnico": "Conferir duração, codecs, áudio, ausência de elementos cortados e sincronismo",
    "qa_conteudo": "Verificar fatos, duplicações de pauta, coerência, copyright, metadados e linguagem",
    "aprovacao": "Encaminhar pacote à aprovação humana; não autorizar upload a partir do planejador",
    "publicacao": "Bloqueada até aprovação e credenciais de upload próprias do canal",
}


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Entrada JSON inválida")
    return value


def channel_policy(channel: str, *, root: Path = ROOT) -> dict:
    managers = read_json(root / "agentes/gerentes-canais.json")
    matches = [x for x in managers["channel_managers"] if x["channel"] == channel]
    if len(matches) != 1:
        raise ValueError("Gerente de canal não cadastrado de modo único")
    cfg = read_json(root / "canal" / channel / "canal.json")
    match = matches[0]
    if cfg.get("id") != channel or cfg.get("youtube", {}).get("channel_id") != match["youtube_channel_id"]:
        raise ValueError("Identidade do canal inválida")
    return {**match, "id": channel}


def build_editorial_plan(channel: str, *, snapshot: dict,
                         candidate_rows: list[dict], root: Path = ROOT) -> dict:
    policy = channel_policy(channel, root=root)
    reservations = read_json(root / "canal" / channel / "editorial/reservas.json")
    chosen = select_idea(snapshot=snapshot, reservations=reservations,
                         candidates=candidate_rows, channel_policy=policy)
    if chosen["status"] != "proposed_for_review":
        return {
            "schema": "videoforge/channel-manager-plan/v1",
            "manager": policy["id"], "channel": channel,
            "status": chosen["status"],
            "metrics": chosen.get("metrics"), "selected": None,
            "tasks": [], "calls_sent": 0, "publish_enabled": False,
        }
    selected = chosen["selected"]
    demand_id = selected.get("id")
    if not isinstance(demand_id, str) or not demand_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("ID da pauta inválido")
    plan = build_plan({
        "id": demand_id,
        "canal": channel,
        "tema": selected["titulo_provisorio"],
        "duracao_segundos": selected["duracao_segundos"],
    }, root=root)
    proxy_bindings = plan_bindings(plan)
    workers = {b["task_id"]: b for b in proxy_bindings["bindings"]}
    for task in plan["tasks"]:
        task.update({
            "channel_manager": policy["id"],
            "channel_scope": channel,
            "instruction": ROLE_INSTRUCTIONS[task["id"]],
            "executor_backend": workers[task["id"]]["backend"],
            "executor_capability": workers[task["id"]]["capability"],
        })
    return {
        "schema": "videoforge/channel-manager-plan/v1",
        "status": "awaiting_editorial_review_and_reservation",
        "channel": channel,
        "channel_id": policy["youtube_channel_id"],
        "manager": policy["id"],
        "selected": selected,
        "evidence": chosen["evidence"],
        "delegation": plan,
        "tasks": plan["tasks"],
        "calls_sent": 0,
        "images_generated": 0,
        "publish_enabled": False,
        "requires_topic_reservation": True,
        "requires_approval": True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Gerente editorial autônomo (planejamento, sem upload)")
    parser.add_argument("--channel", choices=("otaku-br", "otaku-en", "gamer",
                                              "manu-kids", "alchemy-lab"), required=True)
    parser.add_argument("--mode", choices=("offline", "youtube-readonly"), default="offline")
    parser.add_argument("--inventory", type=Path, help="Histórico com fontes YouTube, não um mock público")
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("output/channel-manager/plan.json"))
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args(argv)
    policy = channel_policy(args.channel)
    if args.mode == "offline":
        if not args.inventory:
            raise SystemExit("OFFLINE_REQUIRES_REAL_OR_TEST_INVENTORY")
        snapshot = read_json(args.inventory)
    else:
        # A permissão é somente leitura e o refresh token jamais entra no log.
        import os
        if (os.getenv("CHANNEL_METRICS_READONLY_AUTHORIZED") != "yes"
                or os.getenv("GITHUB_EVENT_NAME") != "workflow_dispatch"
                or os.getenv("GITHUB_REF") != "refs/heads/main"
                or os.getenv("GITHUB_REPOSITORY") != "HelioConde/video-forge-ia"):
            raise SystemExit("READONLY_WORKFLOW_AUTHORIZATION_REQUIRED")
        try:
            access = oauth_access_token(os.getenv("YOUTUBE_CLIENT_JSON", ""),
                                        os.getenv("YOUTUBE_CHANNEL_TOKEN_JSON", ""))
            youtube = YouTubeReadOnly(access_token=access,
                                      expected_channel_id=policy["youtube_channel_id"])
            snapshot = youtube.snapshot(days=args.days)
        except YouTubeReadError as exc:
            raise SystemExit(str(exc)) from None
    proposals = read_json(args.candidates).get("candidates", [])
    if not isinstance(proposals, list):
        raise ValueError("Lista de pautas inválida")
    report = build_editorial_plan(args.channel, snapshot=snapshot, candidate_rows=proposals)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n",
                           encoding="utf-8")
    print("CHANNEL_MANAGER_PLAN_"+report["status"].upper())
    print("NO_PROXY_CALLS_NO_VIDEO_UPLOADS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
