"""Verifica manifests do Pixel Studio antes de publicar no GitHub Pages.

Só conhece schemas públicos e arquivos PNG locais, sem tokens nem IDs externos.
Aceita catálogo parcial, mas nunca imagem corrompida ou hash divergente.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct

ROOT=Path("site/assets/pixellab")
CHARACTERS=ROOT/"agents/alex/production/manifest.json"
OBJECTS=ROOT/"objects/production/manifest.json"
HEADER=b"\x89PNG\r\n\x1a\n"


def _png(path: Path, spec: dict) -> None:
    if not path.is_file() or path.stat().st_size>15*1024*1024:
        raise ValueError("PNG inexistente ou muito grande.")
    data=path.read_bytes()
    if data[:8]!=HEADER or len(data)<29 or data[25]!=6:
        raise ValueError("Assinatura ou formato PNG inválido.")
    width,height=struct.unpack(">II",data[16:24])
    if (width,height)!=(spec.get("width"),spec.get("height")):
        raise ValueError("Dimensão PNG divergente.")
    if hashlib.sha256(data).hexdigest()!=spec.get("sha256"):
        raise ValueError("Hash PNG divergente.")


def verify(root: Path=ROOT) -> dict:
    stats={"alex_motions":0,"alex_directions":0,"objects":0,"object_pngs":0}
    char_file=root/"agents/alex/production/manifest.json"
    if char_file.exists():
        manifest=json.loads(char_file.read_text(encoding="utf-8"))
        if manifest.get("schema")!="videoforge/pixellab-production-atlas/v1":
            raise ValueError("Schema inválido de sprites Alex.")
        for name,item in manifest["motions"].items():
            if not name.replace("_","").isalnum() or item.get("file")!=name+".png":
                raise ValueError("Nome de animação não permitido.")
            _png(char_file.parent/item["file"],item)
            stats["alex_motions"]+=1
            stats["alex_directions"]+=len(item["directions"])
    obj_file=root/"objects/production/manifest.json"
    if obj_file.exists():
        manifest=json.loads(obj_file.read_text(encoding="utf-8"))
        if manifest.get("schema")!="videoforge/pixellab-object-library/v1":
            raise ValueError("Schema inválido de objetos.")
        for name,object_spec in manifest["objects"].items():
            if name not in ("office-chair","cabinet"):
                raise ValueError("Objeto não aprovado.")
            stats["objects"]+=1
            for item in object_spec["files"]:
                namefile=item.get("file","")
                if not namefile.startswith(name+"/") or ".." in namefile or "/" in namefile[len(name)+1:]:
                    raise ValueError("PNG de objeto fora da pasta permitida.")
                _png(obj_file.parent/namefile,item)
                stats["object_pngs"]+=1
    return stats


def main() -> None:
    result=verify()
    output=Path("output/pixellab-production/asset-validation.json")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("PIXELLAB_ASSETS_VALIDATED="+json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
