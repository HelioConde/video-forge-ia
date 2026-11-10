"""Recepção segura das animações do Alex exportadas pelo PixelLab (somente GET).

Aceita lotes parciais: publica SOMENTE movimentos com todas as direções e
quatro frames verificados; preserva atlas previamente importados e nunca
publica UUID, prompts, URLs ou ZIPs na árvore do site.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

from videoforge.pixellab.production_animations import read_catalog
from videoforge.pixellab.cli import DIRECTIONS

FRAME_SIZE = 88
FRAMES = 4
MAX_FRAME_SIZE = 1_048_576
MAX_TOTAL_UNCOMPRESSED = 150 * 1024 * 1024
MAX_ENTRIES = 2500
OUT = Path("site/assets/pixellab/agents/alex/production")
FINGERPRINT = "9708e3207969cd208f819d20d74960fa07d88b7df17470da4c7d303f0fd08a45"
SCHEMA = "videoforge/pixellab-production-atlas/v1"


def _validate_zip(source: ZipFile) -> set[str]:
    entries = source.infolist()
    names = [entry.filename for entry in entries]
    if len(names) != len(set(names)) or len(names) > MAX_ENTRIES:
        raise ValueError("ZIP repetido ou com arquivos demais.")
    if sum(info.file_size for info in entries) > MAX_TOTAL_UNCOMPRESSED:
        raise ValueError("ZIP excede o limite de dados descompactados.")
    return set(names)


def _verified_old(output: Path, catalog: dict) -> dict[str, dict]:
    """Não apagar animações previamente aprovadas se ZIP novo estiver parcial."""
    manifest_path = output / "manifest.json"
    if not manifest_path.exists():
        return {}
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or data.get("character") != "alex" or data.get("frames") != FRAMES:
        raise ValueError("Manifesto anterior incompatível.")
    if (data.get("frameWidth"), data.get("frameHeight")) != (FRAME_SIZE, FRAME_SIZE):
        raise ValueError("Frame de atlas anterior incompatível.")
    old = {}
    for motion, spec in data.get("motions", {}).items():
        plan = catalog.get(motion)
        if not plan or spec.get("file") != motion + ".png":
            raise ValueError("Manifesto anterior contém animação não aprovada.")
        if spec.get("directions") != plan["directions"]:
            raise ValueError("Direções antigas não coincidem com o catálogo.")
        image = output / spec["file"]
        if not image.is_file() or hashlib.sha256(image.read_bytes()).hexdigest() != spec.get("sha256"):
            raise ValueError("Atlas anterior ausente ou alterado: " + motion)
        old[motion] = spec
    return old


def _build_atlas(source: ZipFile, names: set[str], motion: str, directions: list[str]):
    from PIL import Image

    paths = [
        f"Idle/animations/{motion}/{direction}/frame_{index:03}.png"
        for direction in directions for index in range(FRAMES)
    ]
    if any(name not in names for name in paths):
        return None

    atlas = Image.new("RGBA", (FRAME_SIZE * FRAMES, FRAME_SIZE * len(directions)))
    for row, direction in enumerate(directions):
        for col in range(FRAMES):
            key = f"Idle/animations/{motion}/{direction}/frame_{col:03}.png"
            if source.getinfo(key).file_size > MAX_FRAME_SIZE:
                raise ValueError("Frame PNG maior que o limite.")
            frame = Image.open(io.BytesIO(source.read(key)))
            frame.load()
            if frame.mode != "RGBA" or frame.size != (FRAME_SIZE, FRAME_SIZE) or not frame.getbbox():
                raise ValueError("Frame inválido (dimensão/cor/transparência): " + motion)
            atlas.paste(frame, (col * FRAME_SIZE, row * FRAME_SIZE))
    binary = io.BytesIO()
    atlas.save(binary, "PNG", optimize=True)
    return binary.getvalue()


def produce_atlases(zip_path: Path, output: Path = OUT, *, require_all: bool = False) -> dict:
    catalog = [item for item in read_catalog() if item["kind"] == "character"]
    by_motion = {item["motion"]: item for item in catalog}
    previous = _verified_old(output, by_motion)
    result = {
        "schema": SCHEMA,
        "character": "alex",
        "frameWidth": FRAME_SIZE,
        "frameHeight": FRAME_SIZE,
        "frames": FRAMES,
        "expectedMotionCount": len(catalog),
        "motions": {},
    }
    pending = []
    fresh = {}
    with ZipFile(zip_path) as source:
        names = _validate_zip(source)
        metadata = json.loads(source.read("metadata.json"))
        states = metadata.get("states")
        if not isinstance(states, list) or not any(
            isinstance(s, dict) and isinstance(s.get("character"), dict)
            and isinstance(s["character"].get("id"), str)
            and hashlib.sha256(s["character"]["id"].encode("utf-8")).hexdigest() == FINGERPRINT
            for s in states
        ):
            raise ValueError("ZIP não corresponde ao personagem Alex autorizado.")

        for item in catalog:
            motion, directions = item["motion"], item["directions"]
            if not set(directions) <= set(DIRECTIONS):
                raise ValueError("Direção não conhecida no catálogo.")
            blob = _build_atlas(source, names, motion, directions)
            if blob is None:
                if motion in previous:
                    result["motions"][motion] = previous[motion]
                else:
                    pending.append(motion)
                continue
            spec = {
                "file": motion + ".png",
                "directions": directions,
                "width": FRAME_SIZE * FRAMES,
                "height": FRAME_SIZE * len(directions),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "category": item["category"],
            }
            result["motions"][motion] = spec
            fresh[motion] = blob

    if require_all and pending:
        raise ValueError("Exportação incompleta; nenhuma imagem foi escrita.")

    result["availableMotionCount"] = len(result["motions"])
    result["pendingMotionCount"] = len(pending)
    result["pendingMotions"] = pending
    result["availableDirectionCount"] = sum(
        len(item["directions"]) for item in result["motions"].values()
    )
    result["status"] = "complete" if not pending else "partial"

    # Validar o conjunto antes de escrever; gravar manifest por último.
    if result["motions"]:
        output.mkdir(parents=True, exist_ok=True)
        for motion, blob in fresh.items():
            target = output / (motion + ".png")
            if not target.is_file() or target.read_bytes() != blob:
                target.write_bytes(blob)
        manifest = output / "manifest.json"
        rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if not manifest.exists() or manifest.read_text(encoding="utf-8") != rendered:
            manifest.write_text(rendered, encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Receber sprites gerados, sem criar animações")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", default=OUT, type=Path)
    parser.add_argument("--require-all", action="store_true")
    args = parser.parse_args()
    info = produce_atlases(args.source, args.output, require_all=args.require_all)
    summary = {
        "schema": "videoforge/pixellab-production-ingest-summary/v1",
        "status": info["status"],
        "received_motions": info["availableMotionCount"],
        "remaining_motions": info["pendingMotionCount"],
        "received_directions": info["availableDirectionCount"],
        "expected_motions": info["expectedMotionCount"],
    }
    path = Path("output/pixellab-production/receive-summary.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PIXELLAB_RECEIVE=" + json.dumps(summary, sort_keys=True))
    import os
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary_file:
            summary_file.write("## Sprites Alex recebidos (somente GET)\n\n")
            summary_file.write(
                f"Importados: **{summary['received_motions']}/{summary['expected_motions']} movimentos** "
                f"({summary['received_directions']} direções). "
                f"Faltando: **{summary['remaining_motions']}**.\n"
            )


if __name__ == "__main__":
    main()
