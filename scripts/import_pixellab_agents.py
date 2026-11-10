"""Importa frames existentes do PixelLab em atlases estáticos para o GitHub Pages.

Não chama nenhuma API paga. Não inclui IDs, nomes privados, prompts ou URLs nos
assets publicados. Formato: 4 frames na horizontal, 8 direções na vertical.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

from PIL import Image

DIRECTIONS = (
    "south", "south-east", "east", "north-east",
    "north", "north-west", "west", "south-west",
)
MOTIONS = ("idle", "walk", "type", "sit", "talk", "wave")
FRAMES = 4
FINGERPRINT = "9708e3207969cd208f819d20d74960fa07d88b7df17470da4c7d303f0fd08a45"
OUTPUT = Path("site/assets/pixellab/agents/alex")
MAX_SIZE = 20 * 1024 * 1024


def import_sprites(export_zip: Path, output: Path = OUTPUT) -> dict:
    if export_zip.stat().st_size > MAX_SIZE:
        raise ValueError("Exportação supera o limite de segurança")
    with zipfile.ZipFile(export_zip) as outer:
        if "character-frames.zip" in outer.namelist():
            raw = outer.read("character-frames.zip")
        elif "metadata.json" in outer.namelist():
            raw = export_zip.read_bytes()
        else:
            raise ValueError("Exportação sem frames de personagem")
    if len(raw) > MAX_SIZE:
        raise ValueError("Arquivo de frames acima do limite")
    with zipfile.ZipFile(io.BytesIO(raw)) as src:
        names = src.namelist()
        if len(names) != len(set(names)) or len(names) > 800:
            raise ValueError("ZIP com arquivos duplicados ou em excesso")
        for item in src.infolist():
            if item.file_size > 512 * 1024:
                raise ValueError("Arquivo individual acima do limite")
        data = json.loads(src.read("metadata.json"))
        ids = [
            state.get("character", {}).get("id", "")
            for state in data.get("states", [])
        ]
        if not ids or not any(hashlib.sha256(ident.encode("utf-8")).hexdigest() ==
                                  FINGERPRINT for ident in ids):
            raise ValueError("A exportação não corresponde à base PixelLab autorizada")

        sheets = {}
        for motion in MOTIONS:
            imgs = []
            for direction in DIRECTIONS:
                for index in range(FRAMES):
                    path = f"Idle/animations/{motion}/{direction}/frame_{index:03}.png"
                    if path not in names:
                        raise ValueError(f"Frame obrigatório ausente: {motion}/{direction}/{index}")
                    raw_png = src.read(path)
                    image = Image.open(io.BytesIO(raw_png))
                    image.load()
                    if image.mode != "RGBA" or image.size != (88, 88):
                        raise ValueError(f"Formato de frame inesperado: {motion}/{direction}")
                    if not image.getbbox():
                        raise ValueError(f"Frame completamente transparente: {motion}/{direction}")
                    imgs.append(image)
            atlas = Image.new("RGBA", (88 * FRAMES, 88 * len(DIRECTIONS)))
            for row in range(len(DIRECTIONS)):
                for col in range(FRAMES):
                    atlas.paste(imgs[row * FRAMES + col], (col * 88, row * 88))
            mem = io.BytesIO()
            atlas.save(mem, "PNG", optimize=True)
            sheets[motion] = mem.getvalue()

    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "videoforge/pixellab-agent-atlas/v1",
        "character": "alex",
        "frameWidth": 88,
        "frameHeight": 88,
        "frames": FRAMES,
        "directions": list(DIRECTIONS),
        "motions": {},
    }
    for motion, image_bytes in sheets.items():
        destination = output / (motion + ".png")
        destination.write_bytes(image_bytes)
        manifest["motions"][motion] = {
            "file": motion + ".png",
            "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "width": 88 * FRAMES,
            "height": 88 * len(DIRECTIONS),
        }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    result = import_sprites(Path(sys.argv[1]))
    print("PIXELLAB_ATLAS_IMPORT_OK:", len(result["motions"]), "movimentos",
          len(result["directions"]), "direções", result["frames"], "frames/direção")
