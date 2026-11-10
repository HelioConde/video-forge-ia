"""Gera os objetos interativos da produtora no PixelLab, sem duplicação.

Cria um armário apenas se não existir; reutiliza a cadeira existente.
Cada POST é seguido por consulta de job e conferência de biblioteca.
Não imprime tokens, IDs privados ou URLs de mídia.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

from .client import PixelLabClient, PixelLabError
from .office_assets import list_all, wait_for_asset

CHAIR = "VideoForge AI - Office Chair 2026"
CABINET = "VideoForge AI - Cabinet 2026"
TASKS = {
    "rotate_chair_left": (CHAIR, "Office chair smoothly swivels to the left, remaining in the same place."),
    "rotate_chair_right": (CHAIR, "Office chair smoothly swivels to the right, remaining in the same place."),
    "open_cabinet": (CABINET, "Wooden office storage cabinet doors swing open, showing the shelves within."),
}


def find(records: list[dict], name: str) -> dict | None:
    matches = [x for x in records if x.get("name") == name]
    if len(matches) > 1:
        raise PixelLabError("Objeto duplicado no PixelLab, escolha manual necessária.")
    return matches[0] if matches else None


def _existing_animations(client: PixelLabClient, oid: str) -> set[str]:
    response = client._request("GET", "/objects/" + oid)
    groups = response.get("animations")
    if not isinstance(groups, list):
        raise PixelLabError("API não informou as animações do objeto.")
    return {str(group.get("display_name") or group.get("animation_name") or "").strip().lower()
            for group in groups if isinstance(group, dict)}


def _validated_id(value: str) -> str:
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError):
        raise PixelLabError("API retornou identificador inválido de objeto.") from None


def build(client: PixelLabClient, *, mode: str = "plan", authorized: bool = False,
          max_paid: int = 4, output: Path = Path("output/pixellab-production/object-build")) -> dict:
    if mode not in ("plan", "generate") or type(max_paid) is not int or not 1 <= max_paid <= 4:
        raise ValueError("Modo ou limite de custos inválido.")
    if mode == "generate" and not authorized:
        raise PixelLabError("Geração exige autorização explícita.")
    records = list_all(client, "objects")
    submitted: list[str] = []
    completed: list[str] = []
    status: dict[str, str] = {}
    paid = 0

    def report(stage: str) -> dict:
        info = {
            "schema": "videoforge/pixellab-production-objects/v1",
            "status": stage, "paid_cap": max_paid,
            "submitted": submitted[:], "completed": completed[:],
            "motions": status.copy(),
        }
        output.mkdir(parents=True, exist_ok=True)
        (output / "report.json").write_text(
            json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return info

    report("planning")
    if mode == "plan":
        for motion,(name,_) in TASKS.items():
            obj = find(records, name)
            if not obj:
                status[motion] = "asset_missing"
            elif obj.get("status") != "completed":
                status[motion] = "asset_not_ready"
            else:
                oid=_validated_id(obj["id"])
                status[motion] = "existing" if motion in _existing_animations(client, oid) else "missing"
        return report("planned_only")

    try:
        for motion,(name,desc) in TASKS.items():
            obj = find(records,name)
            if not obj:
                if name != CABINET:
                    raise PixelLabError("Objeto essencial não encontrado na biblioteca.")
                if paid >= max_paid:
                    status[motion]="waiting_for_budget"
                    break
                # Criar apenas este móvel que não foi encontrado (sem gerar a cadeira).
                res = client._request("POST","/create-object-pro-flash",{
                    "name":CABINET,
                    "description":"Original walnut wood office storage cabinet, two hinged doors and interior shelves, professional cozy 16-bit RPG pixel art prop, low top-down three-quarter camera, transparent background, no text.",
                    "view":"low top-down",
                    "n_directions":1,
                    "image_size":{"width":96,"height":96},
                })
                oid=_validated_id(res.get("object_id"))
                paid+=1
                submitted.append("create_cabinet")
                report("cabinet_submitted")
                wait_for_asset(client,"objects",oid)
                records.append({"id":oid,"name":CABINET,"status":"completed"})
                completed.append("create_cabinet")
                report("cabinet_created")
                obj=find(records,name)
            if obj.get("status")!="completed":
                raise PixelLabError("Objeto não está pronto para animações.")
            oid=_validated_id(obj["id"])
            if motion in _existing_animations(client,oid):
                status[motion]="existing"
                report("skipped_existing")
                continue
            if paid >= max_paid:
                status[motion]="waiting_for_budget"
                break
            answer=client._request("POST","/objects/"+oid+"/animations",{
                "mode":"v3",
                "animation_description":desc,
                "display_name":motion,
                "frame_count":4,
                "keep_first_frame":False,
                # Objetos são de uma direção. Enviar 'directions' causaria HTTP 400.
            })
            ids=answer.get("background_job_ids")
            if isinstance(ids,list) and len(ids)==1:
                job=_validated_id(ids[0])
            elif isinstance(answer.get("background_job_id"),str):
                job=_validated_id(answer["background_job_id"])
            else:
                raise PixelLabError("POST aceito, sem job único; verificar antes de repetir.")
            paid+=1
            submitted.append(motion)
            status[motion]="submitted"
            report("job_submitted")
            client.poll([job],max_seconds=780)
            if motion not in _existing_animations(client,oid):
                raise PixelLabError("Objeto não registrou animação após job. Não repetir automaticamente.")
            status[motion]="created"
            completed.append(motion)
            report("progress")
    except Exception:
        report("interrupted_review_before_retry")
        raise
    return report("completed" if len(completed)+sum(v=="existing" for v in status.values())==3+(1 if "create_cabinet" in completed else 0) else "partial")


def main() -> None:
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("plan","generate"),default="plan")
    args=p.parse_args()
    try:
        api=PixelLabClient(os.environ.get("PIXELLAB_API_TOKEN",""))
        result=build(api,mode=args.mode,
                     authorized=os.getenv("PIXELLAB_OBJECT_GENERATION_AUTHORIZED")=="true")
        print("PIXELLAB_OBJECT_PRODUCTION="+result["status"]+
              " completed="+str(len(result["completed"])))
    except (ValueError,PixelLabError,OSError) as exc:
        p.exit(1,"Produção de objetos interrompida: "+str(exc)+"\n")


if __name__=="__main__":
    main()
