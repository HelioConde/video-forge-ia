"""Auditoria somente leitura das animações sociais/ambientais do PixelLab.

Consulta a base do Alex por hash, nunca imprime UUID, prompt, URL ou token.
A saída identifica movimentos por rótulos declarados na API: não deduz a
presença de uma animação pelo simples nome de outra.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from .client import PixelLabClient, PixelLabError
from .launch import resolve_target

FINGERPRINT = "9708e3207969cd208f819d20d74960fa07d88b7df17470da4c7d303f0fd08a45"
ACTIVITIES = {
    "sing_seated": ("sing", "singing", "vocal", "sing seated", "karaoke"),
    "coffee": ("coffee", "drinking coffee", "sip coffee", "drink coffee"),
    "drink_water": ("water", "drinking water", "drink water"),
    "games": ("game", "gaming", "joystick", "arcade", "controller"),
    "restroom": ("bathroom", "restroom", "toilet", "wash hands"),
    "stand_up": ("stand up", "standing up", "rise from chair"),
    "sit_down": ("sit down", "sitting down"),
    "headphones": ("headphone", "put on headphones"),
    "stretch": ("stretch", "stretching", "yawn"),
    "dance": ("dance", "dancing"),
    "clap": ("clap", "applause", "applauding"),
}
BASE = ("idle", "walk", "type", "sit", "talk", "wave")


def inspect(detail: dict) -> dict:
    groups = detail.get("animations")
    if not isinstance(groups, list):
        raise PixelLabError("A API não forneceu a lista de grupos de animação")
    labels = []
    for group in groups:
        if not isinstance(group, dict):
            raise PixelLabError("Grupo de animação inválido")
        name = str(group.get("display_name") or group.get("animation_name") or group.get("animation_type") or "")
        normalized = " ".join(re.sub(r"[^a-z0-9]+", " ", name.lower()).split())
        labels.append(normalized)
    states = {}
    for activity, synonyms in ACTIVITIES.items():
        states[activity] = any(any(word in label for word in synonyms) for label in labels)
    others = sum(not any(label in {
        "idle", "walking", "walk", "talk", "talking", "type", "typing",
        "sit", "sitting", "wave", "waving",
    } for _ in [0]) for label in labels)
    return {
        "schema": "videoforge/pixellab-social-audit/v1",
        "total_animation_groups": len(groups),
        "recognized_common_group_count": len(groups) - others,
        "unclassified_or_new_groups": others,
        "activities": states,
        "note": "Não encontrado por nome não prova a inexistência de grupos com rótulos não reconhecidos.",
    }


def main() -> None:
    cli = PixelLabClient(os.getenv("PIXELLAB_API_TOKEN", ""))
    cid = resolve_target(cli, FINGERPRINT)
    result = inspect(cli.character(cid))
    print("PIXELLAB_SOCIAL_AUDIT=" + json.dumps(result, ensure_ascii=False, sort_keys=True))
    path = Path("output/pixellab-social-audit/report.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as fp:
            fp.write("## Inventário das animações sociais (somente GET)\n\n")
            fp.write(f"Grupos: **{len(result['activities'])} ações investigadas**, "
                     f"**{result['total_animation_groups']} grupos** no personagem.\n\n")
            for activity, exists in result["activities"].items():
                fp.write(f"- {activity}: {'encontrada por nome' if exists else 'não encontrada por nome'}\n")
            fp.write("\nNenhuma mídia foi gerada e nenhum identificador privado foi divulgado.\n")


if __name__ == "__main__":
    main()
