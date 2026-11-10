"""Recepção de TODAS as imagens aprovadas de cadeira/armário do PixelLab.

Usa exclusivamente GET. Baixa spritesheet autenticado dos objetos concluídos,
valida os PNGs e salva manifestos sem IDs/URLs/nomes privados.
Não sobrescreve os seis objetos originais publicados no site.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from videoforge.pixellab.client import PixelLabClient, PixelLabError
from videoforge.pixellab.office_assets import list_all, _download_preview
from videoforge.pixellab.production_object_build import CHAIR, CABINET, find, _validated_id

OUT = Path("site/assets/pixellab/objects/production")
SOURCE_NAMES = {"office-chair": CHAIR, "cabinet": CABINET}
SCHEMA = "videoforge/pixellab-object-library/v1"
MAX_ZIP_ENTRIES = 100
MAX_UNPACKED_SIZE = 50 * 1024 * 1024
MAX_FILE_SIZE = 10 * 1024 * 1024


def parse_spritesheet(payload: bytes) -> list[tuple[str, bytes, int, int]]:
    """Preserva todas as imagens contidas no ZIP; layout original fica privado."""
    from PIL import Image

    result = []
    with ZipFile(io.BytesIO(payload)) as source:
        items = source.infolist()
        if (len(items) > MAX_ZIP_ENTRIES or
            len({entry.filename for entry in items}) != len(items) or
            sum(entry.file_size for entry in items) > MAX_UNPACKED_SIZE):
            raise ValueError("Exportação de objeto fora dos limites.")
        for entry in sorted(items, key=lambda e:e.filename):
            if not entry.filename.lower().endswith(".png"):
                continue
            if entry.file_size > MAX_FILE_SIZE:
                raise ValueError("PNG de objeto excedeu limite.")
            image = Image.open(io.BytesIO(source.read(entry)))
            image.load()
            if image.width > 4096 or image.height > 4096 or image.width < 1 or image.height < 1:
                raise ValueError("Dimensão PNG inválida.")
            if image.mode not in ("RGBA", "RGB"):
                raise ValueError("Imagem inesperada no spritesheet.")
            image = image.convert("RGBA")
            if not image.getbbox():
                raise ValueError("Spritesheet de objeto totalmente transparente.")
            buffer = io.BytesIO()
            image.save(buffer, "PNG", optimize=True)
            name = f"sprite-{len(result):03}.png"
            result.append((name, buffer.getvalue(), image.width, image.height))
    if not result:
        raise ValueError("Exportação de objeto sem PNG.")
    return result


def _verify_previous(root: Path) -> dict:
    file = root / "manifest.json"
    if not file.is_file():
        return {}
    data = json.loads(file.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or not isinstance(data.get("objects"), dict):
        raise ValueError("Manifesto anterior de objetos incompatível.")
    for slug, entry in data["objects"].items():
        if slug not in SOURCE_NAMES:
            raise ValueError("Objeto estranho no manifesto antigo.")
        for spec in entry.get("files", []):
            rel = spec.get("file")
            if not isinstance(rel, str) or not rel.startswith(slug+"/") or ".." in rel:
                raise ValueError("Caminho de objeto inválido.")
            raw = (root/rel).read_bytes()
            if hashlib.sha256(raw).hexdigest() != spec.get("sha256"):
                raise ValueError("PNG anterior modificado.")
    return data["objects"]


def receive_objects(client: PixelLabClient, output: Path = OUT) -> dict:
    records = list_all(client, "objects")
    objects = _verify_previous(output)
    staged: dict[str, bytes] = {}
    statuses = {}

    for slug, label in SOURCE_NAMES.items():
        record = find(records, label)
        if record is None:
            statuses[slug] = "not_created"
            continue
        if record.get("status") != "completed":
            statuses[slug] = "not_ready"
            continue

        oid = _validated_id(record["id"])
        detail = client._request("GET", "/objects/" + oid)
        try:
            sprites = parse_spritesheet(client.download_object_spritesheet(oid))
        except (PixelLabError, ValueError, BadZipFile):
            sprites = []
        preview = None
        # O preview é opcional; não misturar mídias antigas ou de outros objetos.
        preview_url = detail.get("preview_url") or detail.get("image_url") or record.get("preview_url")
        if preview_url:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                file = Path(tmp)/"preview.png"
                if _download_preview(preview_url, file):
                    from PIL import Image
                    img = Image.open(file); img.load()
                    if img.width<=4096 and img.height<=4096 and img.getbbox():
                        buf = io.BytesIO(); img.convert("RGBA").save(buf,"PNG",optimize=True)
                        preview = ("preview.png",buf.getvalue(),img.width,img.height)

        images = ([preview] if preview else []) + sprites
        if not images:
            statuses[slug] = "awaiting_export" if slug not in objects else "preserved_existing"
            continue
        files=[]
        for name, blob, width, height in images:
            rel=slug+"/"+name
            staged[rel]=blob
            files.append({
                "file":rel,"width":width,"height":height,
                "sha256":hashlib.sha256(blob).hexdigest()
            })
        objects[slug]={
            "status":"spritesheet_available" if sprites else "preview_only",
            "files":files,
            "spritesheetCount":len(sprites),
        }
        statuses[slug]=objects[slug]["status"]

    received = sum(bool(objects.get(slug,{}).get("files")) for slug in SOURCE_NAMES)
    result = {
        "schema":SCHEMA,"objects":objects,
        "availableObjectCount":received,"expectedObjectCount":len(SOURCE_NAMES),
        "status":"complete" if received==len(SOURCE_NAMES) and all(
            objects[slug].get("spritesheetCount",0)>0 for slug in SOURCE_NAMES
        ) else "partial",
    }
    if objects:
        output.mkdir(parents=True, exist_ok=True)
        for relative, blob in staged.items():
            file=output/relative
            file.parent.mkdir(parents=True,exist_ok=True)
            if not file.is_file() or file.read_bytes()!=blob:
                file.write_bytes(blob)
        manifest=output/"manifest.json"
        content=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
        if not manifest.exists() or manifest.read_text(encoding="utf-8")!=content:
            manifest.write_text(content,encoding="utf-8")
    return {"status":result["status"],"objects":statuses,"received":received,"expected":len(SOURCE_NAMES)}


def main() -> None:
    import os
    from videoforge.pixellab.client import PixelLabClient
    api=PixelLabClient(os.getenv("PIXELLAB_API_TOKEN",""))
    status=receive_objects(api)
    summary=Path("output/pixellab-production/object-receive.json")
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("PIXELLAB_OBJECT_RECEIVE="+json.dumps(status,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
