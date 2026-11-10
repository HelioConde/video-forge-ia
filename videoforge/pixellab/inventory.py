"""Auditoria somente leitura da biblioteca PixelLab antes de gerar novas animações.

Relatório público: nomes de personagens, IDs, prompts, URLs, custos e créditos
são omitidos. Apenas movimentos permitidos, direções e quantidades aparecem.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .client import PixelLabClient, PixelLabError
from .cli import DIRECTIONS, load_profile, parse_character_id

MAX_CHARACTERS = 50
MOTIONS = ("idle", "walk", "type", "sit", "talk", "wave")


def normalize_animation(detail: dict[str, Any]) -> dict[str, Any]:
    groups = detail.get("animations")
    count = detail.get("animation_count")
    statuses: dict[str, set[str]] = {motion: set() for motion in MOTIONS}
    other_count = 0
    if not isinstance(groups, list):
        return {"inspecionavel": False, "total_grupos": count if isinstance(count, int) else None,
                "existentes": {}, "faltantes": {}, "outros_grupos": None}
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("Grupo de animação inesperado.")
        name = str(group.get("display_name") or group.get("animation_type") or "").lower().strip()
        # Não presumir que títulos vagos sejam um movimento configurado.
        match = name if name in statuses else None
        if match is None:
            other_count += 1
            continue
        entries = group.get("directions")
        if not isinstance(entries, list):
            raise ValueError("Direções de animação não fornecidas.")
        for entry in entries:
            direction = entry if isinstance(entry, str) else (entry.get("direction") if isinstance(entry, dict) else None)
            if direction in DIRECTIONS:
                statuses[match].add(direction)

    return {
        "inspecionavel": True,
        "total_grupos": len(groups),
        "existentes": {k: sorted(v) for k, v in statuses.items()},
        "faltantes": {k: [direction for direction in DIRECTIONS if direction not in v] for k, v in statuses.items()},
        "outros_grupos": other_count,
    }


def inspect_account(client: PixelLabClient, *, character_id: str = "") -> dict[str, Any]:
    response = client.characters()
    characters = response.get("characters")
    if not isinstance(characters, list):
        raise ValueError("Lista de personagens em formato inesperado.")
    total = response.get("total")
    if not isinstance(total, int):
        raise ValueError("Total de personagens não foi informado.")
    if total > len(characters):
        # API /characters pagina. Não declarar que só existem as páginas recebidas.
        return {"estado": "PAGINACAO_INCOMPLETA", "total_personagens": total, "inspecionados": len(characters)}
    if total > MAX_CHARACTERS:
        return {"estado": "LIMITE_DE_AUDITORIA", "total_personagens": total, "inspecionados": 0}

    preferred = parse_character_id(character_id) if character_id else None
    explicit = [row for row in characters if isinstance(row, dict) and row.get("id") == preferred] if preferred else []
    alex = [row for row in characters if isinstance(row, dict)
            and str(row.get("name", "")).strip().casefold() in {"alex", "alex — videoforge ai", "alex - videoforge ai"}]
    if preferred:
        if len(explicit) != 1:
            raise ValueError("Personagem escolhido no Secret não foi encontrado na biblioteca.")
        selected = explicit
        selection = "secret"
    elif len(alex) == 1:
        selected = alex
        selection = "nome_alex"
    elif len(characters) == 1:
        selected = characters
        selection = "unico_personagem"
    else:
        selected = []
        selection = "ambiguo" if characters else "biblioteca_vazia"

    summary: dict[str, Any] = {
        "estado": "CONCLUIDO",
        "total_personagens": total,
        "candidatos_alex": len(alex),
        "selecao": selection,
        "personagens_inspecionados": len(selected),
        "estados_totais_na_biblioteca": sum(
            1 for row in characters if isinstance(row, dict) and row.get("state_name")
        ),
    }
    if not selected and characters:
        # Verificar TODAS as bases de forma anônima, sem escolher uma por engano.
        catalog = []
        for idx, row in enumerate(sorted(characters, key=lambda item: (
            str(item.get("created_at", "")), str(item.get("id", "")))), start=1):
            if not isinstance(row, dict):
                raise ValueError("Entrada da biblioteca malformada.")
            detail = client.character(parse_character_id(row["id"]))
            analyzed = normalize_animation(detail)
            catalog.append({
                "indice": idx,
                "estado_da_base": detail.get("status") if detail.get("status") in
                    ("completed", "pending", "processing", "failed") else "desconhecido",
                "estado_nomeado": bool(row.get("state_name")),
                "grupos": analyzed["total_grupos"],
                "movimentos": {
                    name: len(directions) for name, directions in analyzed["existentes"].items()
                } if analyzed["inspecionavel"] else None,
                "outras_animacoes": analyzed["outros_grupos"],
            })
        summary["catalogo_anonimo"] = catalog
    if selected:
        cid = parse_character_id(selected[0]["id"])
        detail = client.character(cid)
        summary["animacoes"] = normalize_animation(detail)
        summary["direcoes_base"] = (
            sorted([direction for direction in DIRECTIONS if (detail.get("rotation_urls") or {}).get(direction)])
            if isinstance(detail.get("rotation_urls"), dict) else []
        )
        summary["estado_base"] = str(detail.get("status", "desconhecido")) if detail.get("status") in ("completed", "failed", "pending", "processing") else "desconhecido"
        # 'animation_count' pode contar direções individuais, diferente de grupos.
        summary["contagem_informada_api"] = detail.get("animation_count") if isinstance(detail.get("animation_count"), int) else None
    return summary


def emit_summary(summary: dict[str, Any]) -> str:
    lines = ["## Inventário PixelLab (somente leitura)",
             "", f"Situação: **{summary['estado']}**",
             f"Personagens na biblioteca: **{summary.get('total_personagens', '?')}**",
             f"Seleção da base: **{summary.get('selecao', 'indefinida')}**"]
    report = summary.get("animacoes")
    if report:
        lines.append(f"Grupos de animações: **{report['total_grupos']}**")
        if report["inspecionavel"]:
            lines.extend(["", "| Movimento | Direções existentes | Direções faltantes |", "|---|---|---|"])
            for movement in MOTIONS:
                existing = report["existentes"][movement]
                missing = report["faltantes"][movement]
                lines.append(f"| {movement} | {', '.join(existing) or 'nenhuma'} | {', '.join(missing) or 'nenhuma'} |")
            lines.append(f"Outros grupos não classificados: **{report['outros_grupos']}**")
        else:
            lines.append("A API informou uma contagem, mas não forneceu detalhes suficientes para classificar direções.")
    else:
        catalog = summary.get("catalogo_anonimo")
        if catalog:
            total_known = sum((row["grupos"] or 0) for row in catalog)
            complete = sum(1 for row in catalog if row["movimentos"] is not None)
            animated = sum(1 for row in catalog if (row["grupos"] or 0)>0)
            lines.append(f"Bases com animações: **{animated} de {len(catalog)}**; grupos identificados: **{total_known}**")
            lines.append(f"Bases com direções inspecionáveis: **{complete} de {len(catalog)}**")
            lines.extend(["", "| Personagem anônimo | Grupos | Direções conhecidas por movimento | Outros grupos |",
                          "|---|---:|---|---:|"])
            for row in catalog:
                motions = row["movimentos"]
                label = ", ".join(f"{k}:{v}" for k,v in motions.items() if v) if motions is not None else "desconhecido"
                lines.append(f"| #{row['indice']:02d} | {row['grupos'] if row['grupos'] is not None else '?'} | {label or 'nenhuma'} | {row['outras_animacoes'] if row['outras_animacoes'] is not None else '?'} |")
            lines.append("A numeração é temporária e não identifica um personagem específico fora desta execução.")
        else:
            lines.append("Biblioteca vazia; nenhuma geração iniciada.")
    lines.extend(["", "**Segurança:** nenhum ID, prompt, URL, token ou saldo foi incluído no relatório.",
                  "**Custo:** nenhuma chamada POST, geração ou animação foi realizada."])
    return "\n".join(lines) + "\n"


def main() -> None:
    token = os.getenv("PIXELLAB_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("PIXELLAB_INVENTORY_STATUS=NOT_CONFIGURED")
    try:
        client = PixelLabClient(token)
        summary = inspect_account(client, character_id=os.getenv("PIXELLAB_CHARACTER_ID", "").strip())
        text = emit_summary(summary)
        # Relatório sem IDs ou prompts é seguro para logs do GitHub público.
        print(text)
        dest = os.getenv("GITHUB_STEP_SUMMARY")
        if dest:
            with Path(dest).open("a", encoding="utf-8") as fp:
                fp.write(text)
        if summary["estado"] != "CONCLUIDO":
            raise SystemExit("Inventário incompleto; verificar paginação antes de gerar.")
    except (PixelLabError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit("Falha no inventário PixelLab: " + str(exc)) from None


if __name__ == "__main__":
    main()
