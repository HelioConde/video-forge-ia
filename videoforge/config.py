"""Lê a configuração de um vídeo e resolve o modelo do canal ou do vídeo.

Não inicializa provedores de IA nem acessa o YouTube.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from videoforge.generators import resolve_generator

ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Configuração não encontrada: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Configuração precisa ser um objeto JSON: {path}")
    return value


def _valid_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ValueError(f"{name} deve ser um ID simples (a-z, 0-9 e hífen)")
    return value


def resolve_model(
    channel: dict[str, Any],
    video: dict[str, Any],
    models_root: Path,
) -> dict[str, Any]:
    """Seleciona o modelo do vídeo, ou o padrão do canal, sem fallback silencioso."""
    chosen = video.get("modelo") or channel.get("modelo_padrao")
    name = _valid_id(chosen, "modelo")
    model = _json_object(models_root / name / "modelo.json")
    if model.get("id") != name:
        raise ValueError(f"ID de modelo inconsistente: {name}")
    if not isinstance(model.get("etapas"), dict):
        raise ValueError(f"Modelo sem etapas válidas: {name}")
    return model


def load_video_config(
    path: str | Path,
    root: str | Path = DEFAULT_ROOT,
) -> dict[str, Any]:
    """Carrega canal/<id>/videos/<id>/video.json e resolve seu modelo."""
    root = Path(root).resolve()
    path = Path(path)
    path = (path if path.is_absolute() else root / path).resolve()

    try:
        rel = path.relative_to(root / "canal")
    except ValueError as exc:
        raise ValueError("O vídeo deve estar dentro de canal/") from exc

    if len(rel.parts) != 4 or rel.parts[1] != "videos" or rel.parts[3] != "video.json":
        raise ValueError("Caminho esperado: canal/<id>/videos/<id>/video.json")

    channel_id = _valid_id(rel.parts[0], "canal")
    video_id = _valid_id(rel.parts[2], "vídeo")
    channel = _json_object(root / "canal" / channel_id / "canal.json")
    video = _json_object(path)

    if channel.get("id") != channel_id:
        raise ValueError(f"ID do canal não corresponde à pasta: {channel_id}")
    if video.get("id") != video_id:
        raise ValueError(f"ID do vídeo não corresponde à pasta: {video_id}")

    model = resolve_model(channel, video, root / "modelos")
    generator = resolve_generator(channel, video, root=root)

    config = {
        "canal": {"id": channel_id, "nome": channel.get("nome", channel_id)},
        "modelo": model,
        "video": video.get("video", {}),
        "scenes": video.get("scenes"),
    }
    # Compatibilidade: vídeos legados sem gerador continuam usando seu modelo.
    # Gerador e modelo são dimensões independentes e não ligam IA sozinhos.
    if generator is not None:
        config["gerador"] = generator
    return config
