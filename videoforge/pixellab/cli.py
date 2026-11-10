"""Comando de personagens do VideoForge AI.

Execução padrão = planejamento gratuito. Chamadas pagas exigem --execute
e PIXELLAB_API_TOKEN no ambiente (GitHub Actions Secrets).
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import struct
from uuid import UUID

from .client import PixelLabClient, PixelLabError

ROOT = Path(__file__).resolve().parents[2]
ID = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
DIRECTIONS = ("south", "south-east", "east", "north-east", "north",
              "north-west", "west", "south-west")
OPERATIONS = ("plan", "create", "animate", "state", "create-and-animate", "ensure-and-animate", "export")


def load_profile(slug: str, *, root: Path = ROOT) -> dict:
    if not ID.fullmatch(slug):
        raise ValueError("ID de personagem inválido.")
    p = root / "personagens" / slug / "profile.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("id") != slug:
        raise ValueError("Perfil de personagem inconsistente.")
    prompt = data.get("description")
    if not isinstance(prompt, str) or not 1 <= len(prompt) <= 2000:
        raise ValueError("Descrição deve ter de 1 a 2000 caracteres.")
    size = data.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or not 32 <= size <= 256 or size % 4:
        raise ValueError("Tamanho do sprite deve ser múltiplo de 4, entre 32 e 256.")
    if data.get("view") not in ("side", "low top-down", "high top-down"):
        raise ValueError("Perspectiva inválida.")
    motions = data.get("motions")
    if not isinstance(motions, dict) or not motions:
        raise ValueError("Nenhuma animação configurada.")
    for name, caption in motions.items():
        if not ID.fullmatch(name) or not isinstance(caption, str) or not 1 <= len(caption) <= 500:
            raise ValueError("Animação inválida no perfil.")
    states = data.get("states", {})
    if not isinstance(states, dict) or not states:
        raise ValueError("Perfil sem estados de pose.")
    for name, caption in states.items():
        if not ID.fullmatch(name) or not isinstance(caption, str) or not 1 <= len(caption) <= 1000:
            raise ValueError("Estado inválido no perfil.")
    return data


def parse_character_id(value: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("ID do PixelLab inválido (esperado UUID).") from exc


def reference_image(profile: dict, slug: str, root: Path = ROOT) -> dict | None:
    path = profile.get("reference_file")
    if path is None:
        return None
    if not isinstance(path, str) or not path.endswith(".png"):
        raise ValueError("A referência precisa ser um PNG local.")
    folder = (root / "personagens" / slug).resolve()
    target = (folder / path).resolve()
    if not target.is_relative_to(folder):
        raise ValueError("Referência fora da pasta do personagem.")
    raw = target.read_bytes()
    if len(raw) > 2_000_000 or raw[:8] != b"\x89PNG\r\n\x1a\n" or len(raw) < 24:
        raise ValueError("Referência deve ser PNG válido com até 2 MB.")
    width, height = struct.unpack(">II", raw[16:24])
    if not 16 <= width <= 256 or not 16 <= height <= 256:
        raise ValueError("O sprite base PixelLab precisa ter dimensões até 256x256.")
    return {"base64": "data:image/png;base64," + base64.b64encode(raw).decode("ascii")}


def write_manifest(folder: Path, data: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def plan(slug: str, profile: dict, operation: str, motion: str, direction: str,
         *, character_id: str | None) -> dict:
    # Este plano não contém token, prompt confidencial nem um ID reutilizável.
    return {
        "schema": "videoforge/pixellab-run/v1",
        "character": slug,
        "operation": operation,
        "motion": motion if operation in ("animate", "create-and-animate", "ensure-and-animate") else None,
        "direction": direction,
        "sprite_size": profile["size"],
        "source": "existing_pixel_lab_character" if character_id else (
            "local_reference" if profile.get("reference_file") else "generate_from_description"
        ),
        "paid_requests_cap": 2,
        "status": "planned_only",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "warning": "Planejamento grátis; nenhuma API de geração foi executada.",
    }


def discover_existing(client: PixelLabClient, profile: dict) -> str | None:
    """Recupera uma base antiga apenas se for possível identificá-la sem adivinhação."""
    response = client.characters()
    characters = response.get("characters")
    if not isinstance(characters, list):
        raise PixelLabError("Inventário da conta PixelLab em formato inesperado.")
    total = response.get("total", len(characters))
    if total != len(characters):
        raise PixelLabError(
            "Existem mais personagens do que o inventário retornou. "
            "Configure PIXELLAB_CHARACTER_ID para selecionar a base correta."
        )
    matching = [
        item for item in characters
        if isinstance(item, dict) and
        str(item.get("name", "")).casefold() in {
            profile.get("name", "").casefold(), profile.get("id", "").casefold()
        }
    ]
    matches = matching if matching else characters
    if len(matches) != 1:
        if not matches:
            return None
        raise PixelLabError(
            "Vários personagens na conta; não vou escolher um aleatório. "
            "Configure PIXELLAB_CHARACTER_ID uma vez no GitHub Secrets."
        )
    return parse_character_id(matches[0]["id"])


def generate(profile: dict, slug: str, client: PixelLabClient,
             folder: Path, info: dict, *, root: Path = ROOT) -> str:
    body = client.create(
        profile["description"],
        name=profile.get("name", slug),
        size=profile["size"],
        view=profile["view"],
        reference=reference_image(profile, slug, root=root),
    )
    character_id = parse_character_id(body["character_id"])
    job_id = parse_character_id(body["background_job_id"])
    info.update({"status": "creation_pending", "character_id": character_id,
                 "creation_job_id": job_id})
    write_manifest(folder, info)
    client.poll([job_id])
    info["status"] = "created"
    write_manifest(folder, info)
    return character_id


def create_state(client: PixelLabClient, character_id: str, profile: dict, state_name: str,
                 folder: Path, info: dict) -> str:
    response = client.state(
        character_id, name=state_name, description=profile["states"][state_name]
    )
    new_id = parse_character_id(response["character_id"])
    job_id = parse_character_id(response["background_job_id"])
    info.update({"status": "state_pending", "base_character_id": character_id,
                 "character_id": new_id, "state_job_id": job_id, "state": state_name})
    write_manifest(folder, info)
    client.poll([job_id])
    info["status"] = "state_created"
    write_manifest(folder, info)
    return new_id


def animate(client: PixelLabClient, character_id: str, profile: dict, motion: str,
            direction: str, folder: Path, info: dict) -> None:
    response = client.animate(
        character_id, name=motion, description=profile["motions"][motion],
        direction=direction, frame_count=4,
    )
    jobs = response.get("background_job_ids")
    if not isinstance(jobs, list) or len(jobs) != 1:
        raise PixelLabError("API não retornou exatamente um job de animação.")
    ids = [parse_character_id(j) for j in jobs]
    info.update({"status": "animation_pending",
                 "animation_jobs": ids,
                 "animation_group_id": response.get("animation_group_id")})
    write_manifest(folder, info)
    client.poll(ids)
    info["status"] = "animated"
    write_manifest(folder, info)


def export(client: PixelLabClient, character_id: str, folder: Path,
           info: dict) -> None:
    for name, kind in (("character-frames.zip", False), ("spritesheet.zip", True)):
        (folder / name).write_bytes(client.download(character_id, spritesheet=kind))
    info["status"] = "completed"
    info["exports"] = ["character-frames.zip", "spritesheet.zip"]
    write_manifest(folder, info)


def run(operation: str, slug: str, motion: str, direction: str, *,
        state_name: str = "sitting", execute: bool = False, character_id: str = "", output: Path | None = None,
        root: Path = ROOT, client: PixelLabClient | None = None) -> dict:
    if operation not in OPERATIONS or direction not in DIRECTIONS:
        raise ValueError("Operação ou direção inválida.")
    profile = load_profile(slug, root=root)
    if motion not in profile["motions"]:
        raise ValueError("Movimento não definido em personagens/" + slug + "/profile.json.")
    if state_name not in profile["states"]:
        raise ValueError("Estado de pose não definido no perfil.")
    current = parse_character_id(character_id) if character_id else None
    folder = output if output is not None else root / "output" / "pixellab" / slug
    info = plan(slug, profile, operation, motion, direction, character_id=current)
    if operation == "plan" or not execute:
        write_manifest(folder, info)
        return info

    token = os.environ.get("PIXELLAB_API_TOKEN", "").strip()
    if client is None:
        client = PixelLabClient(token)
    # Em repo público não persista character_id nos arquivos Git versionados.
    # Sem segredo configurado, tenta descobrir uma única base correspondente na conta.
    if operation in ("animate", "state", "export", "ensure-and-animate") and current is None:
        current = discover_existing(client, profile)
    if operation in ("animate", "state", "export") and current is None:
        raise PixelLabError(
            "Nenhum personagem reutilizável encontrado. Configure PIXELLAB_CHARACTER_ID "
            "ou escolha create-and-animate para gerar uma nova base."
        )
    if operation == "create":
        current = generate(profile, slug, client, folder, info, root=root)
    elif operation == "create-and-animate":
        current = generate(profile, slug, client, folder, info, root=root)
        animate(client, current, profile, motion, direction, folder, info)
    elif operation == "ensure-and-animate":
        if current is None:
            current = generate(profile, slug, client, folder, info, root=root)
        else:
            client.character(current)  # Verifica acesso ao personagem base existente.
        animate(client, current, profile, motion, direction, folder, info)
    elif operation == "animate":
        client.character(current)
        animate(client, current, profile, motion, direction, folder, info)
    elif operation == "state":
        client.character(current)
        current = create_state(client, current, profile, state_name, folder, info)
    elif operation == "export":
        client.character(current)
    export(client, current, folder, info)
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description="PixelLab: planejar, gerar e animar sprites")
    parser.add_argument("--operation", choices=OPERATIONS, default="plan")
    parser.add_argument("--character", default="alex")
    parser.add_argument("--motion", default="idle")
    parser.add_argument("--direction", choices=DIRECTIONS, default="south")
    parser.add_argument("--state", default="sitting")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute", action="store_true",
                        help="Autoriza chamadas pagas; exige PIXELLAB_API_TOKEN")
    args = parser.parse_args()
    try:
        info = run(args.operation, args.character, args.motion, args.direction,
                   state_name=args.state, execute=args.execute,
                   character_id=os.environ.get("PIXELLAB_CHARACTER_ID", ""),
                   output=args.output)
    except (PixelLabError, ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
        parser.exit(1, "Erro PixelLab: " + str(exc) + "\n")
    print("PixelLab:", info["status"], "|", info["character"])
    if not args.execute:
        print("Nenhuma cobrança ou geração realizada (dry-run).")
    else:
        print("Operação concluída; verifique o artefato do GitHub Actions.")


if __name__ == "__main__":
    main()
