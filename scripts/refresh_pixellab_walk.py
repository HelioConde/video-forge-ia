"""Importa o Walking CERTO do estado 'walk' do PixelLab, não do 'Idle'.

Exportação somente GET. A seleção exige estado walk + animação walking,
8 direções e 8 quadros por direção; nunca recorre à variante antiga.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

DIRECTIONS = ("south", "south-east", "east", "north-east",
              "north", "north-west", "west", "south-west")
FINGERPRINT = "9708e3207969cd208f819d20d74960da4c7d303f0fd08a45"
ROOT = Path("site/assets/pixellab/agents/alex")
SOURCE_STATE = "walk"
SOURCE_ANIMATION = "walking"
MAX_ZIP_SIZE = 500 * 1024 * 1024
FRAME_BYTES_LIMIT = 1024 * 1024


def _find_state_animation(names: set[str], state: str, animation: str) -> str | None:
    """Identifica o diretório do ESTADO, nunca o grupo Idle ou outra variante."""
    matches = set()
    for path in names:
        parts = path.split("/")
        if (len(parts) == 5 and parts[0].casefold() == state.casefold()
                and parts[1] == "animations"
                and parts[2].casefold() == animation.casefold()
                and parts[3] in DIRECTIONS and parts[4].startswith("frame_")):
            matches.add((parts[0], parts[2]))
    if len(matches) > 1:
        raise ValueError("Múltiplas variantes com nome ambíguo para o estado walk.")
    if not matches:
        return None
    folder, motion = next(iter(matches))
    return folder + "/animations/" + motion


def replace_walk(source: Path, root: Path = ROOT, *,
                 state: str = SOURCE_STATE, animation: str = SOURCE_ANIMATION,
                 fingerprint: str = FINGERPRINT,
                 attestation: Path | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,49}", state) or not re.fullmatch(
        r"[a-z][a-z0-9_]{1,49}", animation
    ):
        raise ValueError("Estado ou animação inválidos.")
    file = root / "manifest.json"
    manifest = json.loads(file.read_text(encoding="utf-8"))
    if (manifest.get("schema") != "videoforge/pixellab-agent-atlas/v1"
            or manifest.get("character") != "alex" or manifest.get("frames") != 4
            or manifest.get("frameWidth") != 88 or manifest.get("frameHeight") != 88
            or manifest.get("directions") != list(DIRECTIONS)):
        raise ValueError("Manifesto original incompatível.")
    entry = manifest["motions"]["walk"]
    old = root / "walk.png"
    old_count = entry.get("frames", manifest["frames"])
    if (entry.get("file") != "walk.png" or old_count not in (4, 8)
            or entry.get("width") != 88 * old_count or entry.get("height") != 704
            or hashlib.sha256(old.read_bytes()).hexdigest() != entry.get("sha256")):
        raise ValueError("Atlas atual é inválido; não substituir.")

    # Em exportações de grupos, cada estado possui ID próprio. A prova assinada
    # pelo fluxo local de exportação guarda SHA do arquivo e da base validada
    # em resolve_target, sem expor IDs ou chaves.
    verified_by_exporter = False
    if attestation is not None:
        certificate = json.loads(attestation.read_text(encoding="utf-8"))
        if (certificate.get("schema") != "videoforge/pixellab-export-attestation/v1"
                or certificate.get("character_sha256") != fingerprint
                or certificate.get("zip_sha256") != hashlib.sha256(source.read_bytes()).hexdigest()):
            raise ValueError("Prova de exportação inválida ou arquivo alterado.")
        verified_by_exporter = True

    with ZipFile(source) as archive:
        infos = archive.infolist()
        if (len(infos) > 4000 or len({item.filename for item in infos}) != len(infos)
                or sum(item.file_size for item in infos) > MAX_ZIP_SIZE):
            raise ValueError("ZIP excessivo ou duplicado.")
        metadata = json.loads(archive.read("metadata.json"))
        states = metadata.get("states", [])
        metadata_matches = isinstance(states, list) and any(
            isinstance(s, dict) and isinstance(s.get("character"), dict)
            and isinstance(s["character"].get("id"), str)
            and hashlib.sha256(s["character"]["id"].encode()).hexdigest() == fingerprint
            for s in states
        )
        if not verified_by_exporter and not metadata_matches:
            raise ValueError("A exportação não corresponde ao Alex autorizado.")

        names = set(archive.namelist())
        prefix = _find_state_animation(names, state, animation)
        if prefix is None:
            # Exibir apenas os nomes de estados esperados, não pastas contendo IDs.
            seen = sorted({
                path.split("/")[0].casefold()
                for path in names if "/animations/" in path
                and path.split("/")[0].casefold() in ("walk", "idle")
            })
            return {"status": "selected_state_missing", "sourceState": state,
                    "source": animation, "knownStates": seen, "changed": False}
        required = [f"{prefix}/{direction}/frame_{frame:03}.png"
                    for direction in DIRECTIONS for frame in range(8)]
        if not set(required) <= names:
            return {"status": "incomplete_selected_walk", "sourceState": state,
                    "source": animation, "changed": False}

        atlas = Image.new("RGBA", (704, 704))
        for row, direction in enumerate(DIRECTIONS):
            for col in range(8):
                name = f"{prefix}/{direction}/frame_{col:03}.png"
                if archive.getinfo(name).file_size > FRAME_BYTES_LIMIT:
                    raise ValueError("Frame do estado walk acima do limite.")
                image = Image.open(io.BytesIO(archive.read(name)))
                image.load()
                if image.mode != "RGBA" or image.size != (88, 88) or not image.getbbox():
                    raise ValueError("Frame inválido na caminhada do estado walk.")
                atlas.paste(image, (col * 88, row * 88))

        buffer = io.BytesIO()
        atlas.save(buffer, "PNG", optimize=True)
        payload = buffer.getvalue()
        digest = hashlib.sha256(payload).hexdigest()
        if digest == entry["sha256"] and entry.get("sourceState", "").casefold() == state.casefold():
            return {"status": "unchanged", "sourceState": state,
                    "source": animation, "changed": False}

        manifest["motions"]["walk"].update({
            "sha256": digest, "frames": 8, "width": 704,
            "sourceState": state, "sourceAnimation": animation
        })
        old.write_bytes(payload)
        file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        return {"status": "updated", "sourceState": state,
                "source": animation, "changed": True}


def main() -> None:
    parser = argparse.ArgumentParser(description="Importar Walking do estado walk do PixelLab")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--state", default=SOURCE_STATE)
    parser.add_argument("--animation", default=SOURCE_ANIMATION)
    parser.add_argument("--attestation", type=Path)
    args = parser.parse_args()
    report = replace_walk(args.source, state=args.state, animation=args.animation,
                          attestation=args.attestation)
    out = Path("output/pixellab-production/walk-upgrade.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print("WALK_UPGRADE=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
    if report["status"] in ("selected_state_missing", "incomplete_selected_walk"):
        print("Atenção: nenhum walk foi substituído; a nova Walking não está completa no ZIP.")


if __name__ == "__main__":
    main()
