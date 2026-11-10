"""Consulta recursos necessários às animações de objetos da produtora.

Não gera, altera ou publica IDs e URLs privados. Só inspeciona o patrimônio
existente na biblioteca PixelLab.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

from .client import PixelLabClient, PixelLabError
from .office_assets import list_all

ASSETS = {
    "rotate_chair_left": "VideoForge AI - Office Chair 2026",
    "rotate_chair_right": "VideoForge AI - Office Chair 2026",
    "open_cabinet": "VideoForge AI - Cabinet 2026",
}

def inspect(client: PixelLabClient) -> dict:
    records=list_all(client,"objects")
    statuses={}
    for motion,name in ASSETS.items():
        matching=[x for x in records if x.get("name")==name]
        if len(matching)>1:
            raise PixelLabError("Mais de um objeto com o mesmo nome; escolha manual necessária")
        if not matching:
            statuses[motion]={"status":"object_not_created"}
            continue
        obj=matching[0]
        if obj.get("status")!="completed":
            statuses[motion]={"status":"object_not_ready"}
            continue
        detail=client._request("GET","/objects/"+obj["id"])
        animations=detail.get("animations")
        if not isinstance(animations,list):
            statuses[motion]={"status":"animation_schema_unknown"}
            continue
        names={str(g.get("display_name") or g.get("animation_name") or "").strip().lower()
               for g in animations if isinstance(g,dict)}
        statuses[motion]={"status":"existing" if motion in names else "needs_generation"}
    return {"schema":"videoforge/production-object-audit/v1","objects":statuses}


def main() -> None:
    api=PixelLabClient(os.getenv("PIXELLAB_API_TOKEN",""))
    report=inspect(api)
    output=Path("output/pixellab-production/object-audit.json")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("OBJECT_ANIMATION_AUDIT="+json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
