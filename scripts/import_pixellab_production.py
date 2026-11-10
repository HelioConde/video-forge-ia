"""Exporta animações novas de personagem em atlas PNG sanificados.

Lê a biblioteca já gerada. Não gera imagens, não publica UUIDs/URLs/prompts.
Só finaliza quando todas as direções de personagem do catálogo existem.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

from videoforge.pixellab.production_animations import read_catalog
from videoforge.pixellab.cli import DIRECTIONS

FRAME_SIZE = 88
FRAMES = 4
MAX_FRAME_SIZE = 1024 * 1024
OUT = Path("site/assets/pixellab/agents/alex/production")
FINGERPRINT = "9708e3207969cd208f819d20d74960fa07d88b7df17470da4c7d303f0fd08a45"


def produce_atlases(zip_path: Path, output: Path = OUT) -> dict:
    from PIL import Image
    catalog = [x for x in read_catalog() if x["kind"] == "character"]
    result = {
        "schema": "videoforge/pixellab-production-atlas/v1",
        "character": "alex",
        "frameWidth": FRAME_SIZE,
        "frameHeight": FRAME_SIZE,
        "frames": FRAMES,
        "motions": {},
    }
    written: dict[str, bytes] = {}
    with ZipFile(zip_path) as source:
        metadata = json.loads(source.read("metadata.json"))
        ids = [s.get("character", {}).get("id") for s in metadata.get("states", []) if isinstance(s, dict)]
        if not any(isinstance(cid, str) and
                   hashlib.sha256(cid.encode("utf-8")).hexdigest() == FINGERPRINT
                   for cid in ids):
            raise ValueError("Exportação não pertence ao personagem aprovado.")
        names = set(source.namelist())
        for item in catalog:
            motion, directions = item["motion"], item["directions"]
            atlas = Image.new("RGBA", (FRAME_SIZE * FRAMES, FRAME_SIZE * len(directions)))
            for row, direction in enumerate(directions):
                if direction not in DIRECTIONS:
                    raise ValueError("Direção fora do catálogo")
                for col in range(FRAMES):
                    key = f"Idle/animations/{motion}/{direction}/frame_{col:03}.png"
                    if key not in names:
                        raise ValueError("Animação ainda não concluída: " + motion + "/" + direction)
                    entry = source.getinfo(key)
                    if entry.file_size > MAX_FRAME_SIZE:
                        raise ValueError("Frame maior do que o permitido.")
                    image = Image.open(io.BytesIO(source.read(key)))
                    image.load()
                    if image.mode != "RGBA" or image.size != (FRAME_SIZE, FRAME_SIZE) or not image.getbbox():
                        raise ValueError("Frame não verificável em " + motion + "/" + direction)
                    atlas.paste(image, (col * FRAME_SIZE, row * FRAME_SIZE))
            mem = io.BytesIO()
            atlas.save(mem, "PNG", optimize=True)
            data = mem.getvalue()
            written[motion + ".png"] = data
            result["motions"][motion] = {
                "file": motion + ".png",
                "directions": directions,
                "width": FRAME_SIZE * FRAMES,
                "height": FRAME_SIZE * len(directions),
                "sha256": hashlib.sha256(data).hexdigest(),
                "category": item["category"],
            }
    # Validar todos os arquivos ANTES de gravar: operação tudo ou nada.
    output.mkdir(parents=True, exist_ok=True)
    for name, data in written.items():
        (output / name).write_bytes(data)
    (output / "manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    result = produce_atlases(args.source)
    print(f"PIXELLAB_PRODUCTION_IMPORT_OK={len(result['motions'])} motions")
    summary = Path("output/production-import-summary.json")
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps({
        "motions": len(result["motions"]),
        "directions": sum(len(x["directions"]) for x in result["motions"].values()),
        "status": "imported_validated",
    }, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
