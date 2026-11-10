"""Planejador local de vídeos. Não usa IA nem publica conteúdo.

Esta etapa cria e valida um storyboard determinístico (dry-run).
Os conectores de IA, renderização e upload serão implementados separadamente.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_storyboard(config: dict[str, Any]) -> dict[str, Any]:
    video = config.get("video", {})
    duration = video.get("duration_seconds")
    scenes = config.get("scenes")

    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise ValueError("video.duration_seconds deve ser inteiro positivo")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("scenes deve ser uma lista não vazia")

    timeline: list[dict[str, Any]] = []
    elapsed = 0
    scene_ids: set[str] = set()

    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"Cena {index} deve ser um objeto")
        scene_id = scene.get("id")
        seconds = scene.get("duration_seconds")
        prompt = scene.get("visual_prompt")
        narration = scene.get("narration")

        if not isinstance(scene_id, str) or not scene_id.strip() or scene_id in scene_ids:
            raise ValueError(f"Cena {index}: id vazio ou duplicado")
        if not isinstance(seconds, int) or isinstance(seconds, bool) or seconds <= 0:
            raise ValueError(f"Cena {index}: duração inválida")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Cena {index}: visual_prompt obrigatório")
        if not isinstance(narration, str) or not narration.strip():
            raise ValueError(f"Cena {index}: narration obrigatória")

        scene_ids.add(scene_id)
        timeline.append({
            "id": scene_id,
            "start_seconds": elapsed,
            "end_seconds": elapsed + seconds,
            "duration_seconds": seconds,
            "visual_prompt": prompt,
            "narration": narration,
            "layers": scene.get("layers", []),
            "asset_status": "pending",
        })
        elapsed += seconds

    if elapsed != duration:
        raise ValueError(
            f"A soma das cenas ({elapsed}s) deve ser igual à duração do vídeo ({duration}s)"
        )

    return {
        "project": "VideoForge AI",
        "status": "storyboard_ready_assets_not_generated",
        "mode": "dry-run",
        "video": {
            "duration_seconds": duration,
            "width": video.get("width", 1080),
            "height": video.get("height", 1920),
            "fps": video.get("fps", 30),
            "language": video.get("language", "pt-BR"),
        },
        "timeline": timeline,
        "publishing": {
            "upload_enabled": False,
            "privacy_status": "private",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera storyboard em modo de teste")
    parser.add_argument("--config", default="config/example.json")
    parser.add_argument("--output", default="output/storyboard.json")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    storyboard = build_storyboard(config)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Storyboard validado: {path} (sem geração de mídia ou upload)")


if __name__ == "__main__":
    main()
