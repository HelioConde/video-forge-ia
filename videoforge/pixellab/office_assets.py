"""PixelLab — cenários e objetos reutilizáveis do escritório VideoForge AI.

- O plano é versionado, nunca mídia ou segredos.
- GET inventaria antes de POST; nomes com prefixo específico evitam duplicatas.
- Cenários ficam na biblioteca Rooms; objetos na biblioteca Objects.
- PNGs opcionais vão apenas para artifacts de 7 dias, sem commit público.
- Nunca repetir geração após timeout/resultado ambíguo.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import UUID

from .client import PixelLabClient, PixelLabError

PLAN_PATH = Path("cenarios/escritorio/pixellab-plan.json")
OUT = Path("output/pixellab-office")
STAGES = ("plan", "first", "remaining", "all")
MAX_NEW = 9
ALLOWED_IMAGE_HOSTS = (
    "pixellab.ai", "cloudfront.net", "amazonaws.com",
    "googleapis.com", "storage.googleapis.com", "r2.dev"
)
PENDING = {"processing", "pending", "queued", "generating", "in_progress"}


def read_plan(path: Path = PLAN_PATH) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("project") != "videoforge-pixel-studio":
        raise ValueError("Plano de escritório inesperado.")
    rooms, objects = plan.get("rooms"), plan.get("objects")
    if not isinstance(rooms, list) or not isinstance(objects, list):
        raise ValueError("Plano sem salas/objetos.")
    if len(rooms) != 3 or len(objects) != 6:
        raise ValueError("Este lote está limitado a 3 salas e 6 objetos.")
    names = set()
    for item in [*rooms, *objects]:
        slug = item.get("slug")
        name = item.get("name")
        if (not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9-]{2,40}", slug)
            or not isinstance(name, str) or len(name) > 120
            or not name.startswith("VideoForge AI - ") or name in names):
            raise ValueError("Nome/slug de asset inválido ou duplicado.")
        names.add(name)
    for room in rooms:
        if not 3 <= len(room.get("theme", "")) <= 300:
            raise ValueError("O tema da sala deve ter até 300 caracteres.")
        if room.get("view") != "top-down" or room.get("tile_size") != 32 or room.get("pieces") is not False:
            raise ValueError("Uma sala fora do padrão de projeto.")
        if not room.get("doors"):
            raise ValueError("Sala sem porta.")
    for obj in objects:
        if obj.get("size") not in (64, 96):
            raise ValueError("Tamanho de objeto fora do catálogo.")
        if not 1 <= len(obj.get("description", "")) <= 2000:
            raise ValueError("Descrição de objeto inválida.")
    return plan


def list_all(client: PixelLabClient, kind: str) -> list[dict]:
    if kind not in ("rooms", "objects"):
        raise ValueError("Tipo de biblioteca inválido.")
    entries = []
    offset = 0
    for _ in range(10):
        payload = client._request("GET", f"/{kind}", query={"limit": 100, "offset": offset})
        page = payload.get(kind)
        total = payload.get("total")
        if not isinstance(page, list) or type(total) is not int or total < 0:
            raise PixelLabError("Biblioteca PixelLab retornou paginação inválida.")
        if not all(isinstance(item, dict) for item in page):
            raise PixelLabError("Biblioteca PixelLab retornou itens malformados.")
        entries.extend(page)
        if len(entries) >= total:
            if len(entries) != total:
                raise PixelLabError("Biblioteca PixelLab retornou itens duplicados.")
            return entries
        if not page:
            raise PixelLabError("Biblioteca PixelLab retornou página vazia antes do fim.")
        offset += len(page)
    raise PixelLabError("Biblioteca PixelLab excedeu o limite de 1000 itens.")


def existing_record(records: list[dict], name: str) -> dict | None:
    matches = [row for row in records if row.get("name") == name]
    if len(matches) > 1:
        raise PixelLabError("Mais de um asset com mesmo nome; revisão necessária.")
    return matches[0] if matches else None


def build_queue(plan: dict) -> list[tuple[str, dict]]:
    # A primeira sala fixa o estilo das salas seguintes. Objetos independentes.
    a = plan["rooms"]
    b = plan["objects"]
    return [
        ("rooms", a[0]), ("objects", b[0]), ("objects", b[1]),
        ("rooms", a[1]), ("rooms", a[2]),
        *[("objects", item) for item in b[2:]]
    ]


def _safe_summary(entries: list[dict], *, mode: str, total_found: int) -> dict:
    return {
        "schema": "videoforge/pixellab-office/v1",
        "mode": mode,
        "total_found": total_found,
        "assets": entries,
        "generated": sum(row["status"] == "created" for row in entries),
        "reused": sum(row["status"] == "reused" for row in entries),
        "pending": sum(row["status"] == "pending" for row in entries),
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def save_report(report: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = [
            "## PixelLab — cenários e objetos",
            f"Modo: **{report['mode']}**",
            f"Criados: **{report['generated']}**, existentes: **{report['reused']}**, processando: **{report['pending']}**",
            "",
            "| Tipo | Nome | Situação |",
            "|---|---|---|",
        ]
        for row in report["assets"]:
            lines.append(f"| {row['kind']} | {row['slug']} | {row['status']} |")
        lines.append("\nNenhum token, ID privado ou URL de mídia foi exposto.")
        with Path(summary_path).open("a", encoding="utf-8") as fp:
            fp.write("\n".join(lines) + "\n")


def wait_for_asset(client: PixelLabClient, kind: str, asset_id: str,
                   *, max_seconds: int = 1050,
                   interval: int = 10, sleeper=time.sleep,
                   clock=time.monotonic) -> dict:
    try:
        asset_id = str(UUID(asset_id))
    except (ValueError, TypeError):
        raise PixelLabError("ID da geração inválido.") from None
    deadline = clock() + max_seconds
    while clock() < deadline:
        response = client._request("GET", f"/{kind}/{asset_id}")
        item = response.get("object", response) if kind == "objects" else response.get("room", response)
        if not isinstance(item, dict):
            raise PixelLabError("Resposta inesperada de status de asset.")
        status = item.get("status")
        if status == "completed":
            return item
        if status in {"failed", "cancelled", "canceled", "review"}:
            raise PixelLabError("Asset PixelLab não concluiu automaticamente; revisar a biblioteca.")
        if status not in PENDING:
            raise PixelLabError("Status desconhecido; verificar o job antes de nova cobrança.")
        sleeper(interval)
    raise PixelLabError("Tempo de espera excedido: não repetir POST antes de conferir o asset original.")


def _download_preview(url: str | None, destination: Path) -> bool:
    if not isinstance(url, str) or not url:
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or not any(
        host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_IMAGE_HOSTS
    ):
        return False
    try:
        with urlopen(Request(url, headers={"User-Agent": "VideoForge-PixelLab-Asset/1"}),
                     timeout=35) as response:
            png = response.read(8 * 1024 * 1024 + 1)
        if not png.startswith(b"\x89PNG\r\n\x1a\n") or len(png) > 8 * 1024 * 1024:
            return False
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(png)
        return True
    except (OSError, ValueError):
        return False


def run(client: PixelLabClient, plan: dict, *,
        mode: str = "plan", max_new: int = 3, stage: str = "all",
        authorized: bool = False, report_public: bool = False,
        output: Path = OUT) -> dict:
    if mode not in ("plan", "generate") or stage not in STAGES:
        raise ValueError("Modo/etapa inválido.")
    if type(max_new) is not int or not 1 <= max_new <= MAX_NEW:
        raise ValueError("Limite de 1 a 9 novos assets por execução.")
    if mode == "generate" and (not authorized or not report_public):
        raise PixelLabError("É necessária autorização de custo e do relatório público.")
    room_list = list_all(client, "rooms")
    object_list = list_all(client, "objects")
    room_by_name = {x["name"]: x for x in room_list if x.get("name")}
    records = {"rooms": room_list, "objects": object_list}
    queue = build_queue(plan)
    if stage == "first":
        queue = queue[:3]
    elif stage == "remaining":
        queue = queue[3:]
    rows: list[dict] = []
    created = 0
    def checkpoint() -> dict:
        report = _safe_summary(rows, mode=mode, total_found=len(room_list)+len(object_list))
        save_report(report, output)
        return report
    checkpoint()
    for kind, item in queue:
        slug, name = item["slug"], item["name"]
        existing = existing_record(records[kind], name)
        status = "missing"
        details = None
        if existing:
            status = existing.get("status") or "unknown"
            if status == "completed":
                status = "reused"
                details = existing
            elif status in PENDING:
                if mode == "generate":
                    details = wait_for_asset(client, kind, existing["id"])
                    status = "reused"
                else:
                    status = "pending"
            else:
                raise PixelLabError("Já existe um asset com status que precisa de revisão.")
        elif mode == "generate" and created < max_new:
            # Uma única chamada paga por asset; salvar um marcador público logo após.
            if kind == "rooms":
                payload = {
                    "name": name, "theme": item["theme"], "doors": item["doors"],
                    "view": item["view"], "tile_size": item["tile_size"],
                    "pieces": False,
                }
                source_slug = item.get("inherit_style_from")
                if source_slug:
                    base = next((x for x in plan["rooms"] if x["slug"] == source_slug), None)
                    room_record = existing_record(records["rooms"], base["name"]) if base else None
                    if not room_record:
                        raise PixelLabError("Sala-base ainda não foi criada; interromper para manter estilo.")
                    room_detail = client._request("GET", "/rooms/" + str(UUID(room_record["id"])))
                    if room_detail.get("status") != "completed" or not room_detail.get("can_be_style_room"):
                        raise PixelLabError("Sala-base não está concluída ou não aceita herança de estilo.")
                    payload["style_room_id"] = str(UUID(room_record["id"]))
                answer = client._request("POST", "/create-room", payload)
                key = "room_id"
            else:
                payload = {
                    "description": item["description"], "name": name,
                    "view": "low top-down",
                    "n_directions": 1,
                    "image_size": {"width": item["size"], "height": item["size"]},
                }
                answer = client._request("POST", "/create-object-pro-flash", payload)
                key = "object_id"
            asset_id = answer.get(key)
            if not isinstance(asset_id, str):
                raise PixelLabError("PixelLab aceitou POST mas não devolveu ID: não repetir chamada.")
            rows.append({"kind": kind, "slug": slug, "status": "pending"})
            checkpoint()
            details = wait_for_asset(client, kind, asset_id)
            rows[-1]["status"] = "created"
            created += 1
            # A biblioteca é fonte de verdade para evitar duplicatas entre chamadas.
            new_entry = {"id": asset_id, "name": name, "status": "completed"}
            records[kind].append(new_entry)
            if kind == "rooms":
                room_by_name[name] = new_entry
        if details is not None:
            url = details.get("image_url") if kind == "rooms" else details.get("preview_url")
            if not url and kind == "objects":
                other = list_all(client, "objects")
                matched = existing_record(other, name)
                url = matched.get("preview_url") if matched else None
            path = output / ("scenes" if kind == "rooms" else "objects") / (slug + ".png")
            downloaded = _download_preview(url, path)
        else:
            downloaded = False
        if not rows or rows[-1].get("slug") != slug:
            rows.append({"kind": kind, "slug": slug, "status": status})
        if downloaded:
            rows[-1]["png"] = True
        checkpoint()
    return checkpoint()


def main() -> None:
    parser = argparse.ArgumentParser(description="Escritório PixelLab")
    parser.add_argument("--mode", choices=["plan", "generate"], default="plan")
    parser.add_argument("--stage", choices=STAGES, default="all")
    parser.add_argument("--max-new", type=int, default=3)
    args = parser.parse_args()
    try:
        api = PixelLabClient(os.environ.get("PIXELLAB_API_TOKEN", ""))
        report = run(
            api, read_plan(), mode=args.mode, stage=args.stage, max_new=args.max_new,
            authorized=os.environ.get("PIXELLAB_OFFICE_AUTHORIZED") == "true",
            report_public=os.environ.get("PIXELLAB_PUBLIC_REPORT_AUTHORIZED") == "true"
        )
        print("PIXELLAB_OFFICE_STATUS=completed created=" + str(report["generated"]) +
              " reused=" + str(report["reused"]) + " pending=" + str(report["pending"]))
    except (PixelLabError, ValueError, TypeError, KeyError, OSError) as exc:
        raise SystemExit("PixelLab office interrompido: " + str(exc)) from None


if __name__ == "__main__":
    main()
