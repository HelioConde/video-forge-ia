"""Atualiza somente o atlas walk se uma caminhada PixelLab nova estiver completa."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
from pathlib import Path
from zipfile import ZipFile
from PIL import Image

DIRECTIONS=("south","south-east","east","north-east","north","north-west","west","south-west")
FINGERPRINT="9708e3207969cd208f819d20d74960fa07d88b7df17470da4c7d303f0fd08a45"
PREFERRED=("walk_new","walk_v2","walking_new","walking_v2","walk_cycle_v2",
           "walk_smooth","smooth_walk","walk_cycle","walking_cycle","walking","walk_2","walk")
ROOT=Path("site/assets/pixellab/agents/alex")

def replace_walk(source: Path, root: Path=ROOT, *, preferred: str|None=None,
                 fingerprint: str=FINGERPRINT) -> dict:
    if preferred and not re.fullmatch(r"[a-z][a-z0-9_]{1,49}",preferred):
        raise ValueError("Nome de movimento inválido.")
    file=root/"manifest.json"
    manifest=json.loads(file.read_text(encoding="utf-8"))
    if manifest.get("schema")!="videoforge/pixellab-agent-atlas/v1" or (
        manifest.get("character")!="alex" or manifest.get("frames")!=4 or
        manifest.get("frameWidth")!=88 or manifest.get("frameHeight")!=88 or
        manifest.get("directions")!=list(DIRECTIONS)):
        raise ValueError("Manifesto original incompatível.")
    entry=manifest["motions"]["walk"]
    old=root/"walk.png"
    old_count=entry.get("frames",manifest["frames"])
    if (entry.get("file")!="walk.png" or old_count not in (4,8) or
        entry.get("width")!=88*old_count or entry.get("height")!=704 or
        hashlib.sha256(old.read_bytes()).hexdigest()!=entry.get("sha256")):
        raise ValueError("Walk original inválido; não substituir.")
    with ZipFile(source) as archive:
        infos=archive.infolist()
        if len(infos)>4000 or len({f.filename for f in infos})!=len(infos) or (
            sum(f.file_size for f in infos)>500*1024*1024):
            raise ValueError("Exportação excessiva ou duplicada.")
        meta=json.loads(archive.read("metadata.json"))
        if not any(isinstance(s,dict) and isinstance(s.get("character"),dict)
                   and isinstance(s["character"].get("id"),str)
                   and hashlib.sha256(s["character"]["id"].encode()).hexdigest()==fingerprint
                   for s in meta.get("states",[])):
            raise ValueError("Identidade do Alex não confere.")
        names=set(archive.namelist())
        groups={p.split("/")[2] for p in names if p.startswith("Idle/animations/") and len(p.split("/"))==5}
        for name in ((preferred,) if preferred else PREFERRED):
            if name not in groups: continue
            has_extra=any(
                f"Idle/animations/{name}/{d}/frame_{n:03}.png" in names
                for d in DIRECTIONS for n in range(4,8)
            )
            # A animação PixMinimax chamada "walking" tem oito quadros.
            # Nunca tratá-la como quatro mesmo durante exportação incompleta.
            count=8 if name=="walking" or has_extra else 4
            if count<old_count:
                continue  # Não reduzir uma caminhada já importada de oito quadros.
            required=[f"Idle/animations/{name}/{d}/frame_{n:03}.png"
                      for d in DIRECTIONS for n in range(count)]
            if not set(required)<=names:
                if name!="walk":return {"status":"incomplete","source":name,"changed":False}
                continue
            atlas=Image.new("RGBA",(88*count,704))
            for row,direction in enumerate(DIRECTIONS):
                for col in range(count):
                    key=f"Idle/animations/{name}/{direction}/frame_{col:03}.png"
                    if archive.getinfo(key).file_size>1024*1024:
                        raise ValueError("Frame acima do limite.")
                    img=Image.open(io.BytesIO(archive.read(key)));img.load()
                    if img.mode!="RGBA" or img.size!=(88,88) or not img.getbbox():
                        raise ValueError("Frame de caminhada inválido.")
                    atlas.paste(img,(col*88,row*88))
            buf=io.BytesIO();atlas.save(buf,"PNG",optimize=True)
            data=buf.getvalue();digest=hashlib.sha256(data).hexdigest()
            if digest==entry["sha256"]:
                return {"status":"unchanged","source":name,"changed":False}
            manifest["motions"]["walk"]["sha256"]=digest
            manifest["motions"]["walk"]["frames"]=count
            manifest["motions"]["walk"]["width"]=count*88
            manifest["motions"]["walk"]["sourceAnimation"]=name
            old.write_bytes(data)
            file.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            return {"status":"updated","source":name,"changed":True}
    return {"status":"no_new_walk","source":None,"changed":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--preferred")
    args=p.parse_args()
    result=replace_walk(args.source,preferred=args.preferred)
    output=Path("output/pixellab-production/walk-upgrade.json")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("WALK_UPGRADE="+json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
