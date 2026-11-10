"""Planejamento e geração de novos movimentos do Alex no PixelLab.

O catálogo inclui apenas movimentos de personagem. Sequências compostas e
objetos são identificados como pendências de integração separadas.

Segurança: sem regenerar a base, sem repetir POST em erro/timeout, sem incluir
tokens/UUIDs/URLs em artifact público. Cada chamada é verificada com GET.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from uuid import UUID

from .cli import DIRECTIONS
from .client import PixelLabClient, PixelLabError
from .launch import resolve_target

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "personagens/alex/production-animations.json"
OUT = Path("output/pixellab-production")
MAX_NEW_PER_GROUP = 8
MAX_TOTAL = 145
MOTION = re.compile(r"^[a-z][a-z0-9_]{1,49}$")


def _name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def read_catalog(path: Path = CATALOG) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "videoforge/pixellab-production-catalog/v1" or payload.get("character") != "alex":
        raise ValueError("Catálogo PixelLab desconhecido.")
    entries = payload.get("items")
    if not isinstance(entries, list) or not 100 <= len(entries) <= 180:
        raise ValueError("Catálogo incompleto ou fora do limite.")
    names: set[str] = set()
    for item in entries:
        key = item.get("motion")
        if not isinstance(key, str) or not MOTION.fullmatch(key) or key in names:
            raise ValueError("Ação duplicada ou nome inválido.")
        names.add(key)
        if item.get("kind") not in ("character", "object", "sequence"):
            raise ValueError("Tipo inválido de animação.")
        if item.get("priority") not in (0, 1, 2):
            raise ValueError("Prioridade inválida.")
        direction_list = item.get("directions")
        if not isinstance(direction_list, list) or not direction_list or (
            len(direction_list) != len(set(direction_list)) or
            not set(direction_list) <= set(DIRECTIONS)
        ):
            raise ValueError("Direção inválida em " + key)
        prompt = item.get("description")
        if not isinstance(prompt, str) or not 20 <= len(prompt) <= 500:
            raise ValueError("Prompt em inglês inválido.")
    return entries


def _groups(detail: dict) -> dict[str, dict]:
    groups = detail.get("animations")
    if not isinstance(groups, list):
        raise PixelLabError("API não informou detalhes dos grupos de animação.")
    result: dict[str, dict] = {}
    for entry in groups:
        if not isinstance(entry, dict):
            raise PixelLabError("Grupo PixelLab malformado.")
        # Só considerar nomes exatos; nunca mesclar uma animação 'talk'
        # com uma ação nova como 'talk_explain'.
        label = _name(str(entry.get("display_name") or entry.get("animation_name")
                          or entry.get("animation_type") or ""))
        if not label:
            raise PixelLabError("Nome de grupo não identificado.")
        if label in result:
            raise PixelLabError("Dois grupos com mesmo nome no PixelLab: " + label)
        directions = entry.get("directions")
        if not isinstance(directions, list):
            raise PixelLabError("Direções do grupo ausentes.")
        existing = set()
        for direction in directions:
            d = direction if isinstance(direction, str) else (
                direction.get("direction") if isinstance(direction, dict) else None)
            if d not in DIRECTIONS:
                raise PixelLabError("Direção não reconhecida pela API.")
            existing.add(d)
        raw_id = entry.get("animation_group_id") or entry.get("id")
        try:
            gid = str(UUID(str(raw_id))) if raw_id else None
        except (ValueError, TypeError):
            raise PixelLabError("UUID do grupo inválido; não gerar.") from None
        result[label] = {"directions": existing, "id": gid}
    return result


def plan(detail: dict, catalog: list[dict]) -> dict:
    present = _groups(detail)
    missing = []
    already = []
    separate = []
    for item in sorted(catalog, key=lambda x: (x["priority"], catalog.index(x))):
        kind, name = item["kind"], item["motion"]
        if kind != "character":
            separate.append({"motion": name, "kind": kind})
            continue
        matched = present.get(name)
        for direction in item["directions"]:
            key = {"motion": name, "direction": direction}
            if matched and direction in matched["directions"]:
                already.append(key)
            else:
                if matched and not matched["id"]:
                    raise PixelLabError("Grupo existente sem UUID, não arriscar duplicação.")
                missing.append(key)
    return {"pending": missing, "existing": already, "separate": separate}


def write_report(output: Path, *, status: str, planned: dict,
                 attempted: list, finished: list, cap: int) -> dict:
    # Sem grupo/character/job UUID, links de imagem, token ou prompt privado.
    result = {
        "schema": "videoforge/pixellab-production-generation/v1",
        "status": status,
        "cap": cap,
        "existing_before": len(planned["existing"]),
        "missing_before": len(planned["pending"]),
        "sequence_or_object_actions": len(planned["separate"]),
        "submitted": attempted[:],
        "completed": finished[:],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as f:
            f.write("## PixelLab — novas animações da produtora\n\n")
            f.write(f"Resultado: **{status}**. Existentes: **{len(planned['existing'])}**, "
                    f"faltantes no começo: **{len(planned['pending'])}**, "
                    f"concluídas nesta execução: **{len(finished)}**, "
                    f"limite de cobranças: **{cap}**.\n\n")
            f.write("Nenhum ID privado ou prompt foi exportado.\n")
    return result


def run(client: PixelLabClient, cid: str, catalog: list[dict], *,
        mode: str = "plan", max_new: int = 8,
        authorized: bool = False, public_report: bool = False,
        output: Path = OUT, sleeper=time.sleep) -> dict:
    if mode not in ("plan", "generate") or type(max_new) is not int or not 1 <= max_new <= MAX_TOTAL:
        raise ValueError("Modo ou limite inválidos.")
    if mode == "generate" and not (authorized and public_report):
        raise PixelLabError("Geração requer autorização explícita de custo e relatório.")
    first = plan(client.character(cid), catalog)
    attempted: list[dict] = []
    finished: list[dict] = []

    def save(status: str) -> dict:
        return write_report(output, status=status, planned=first,
                            attempted=attempted, finished=finished, cap=max_new)

    save("planned")
    if mode == "plan":
        return save("planned_only")
    by_name = {x["motion"]: x for x in catalog}
    pending = first["pending"][:max_new]
    try:
        for index, wanted in enumerate(pending):
            name, direction = wanted["motion"], wanted["direction"]
            fresh = _groups(client.character(cid))
            group = fresh.get(name)
            if group and direction in group["directions"]:
                continue
            if group and not group["id"]:
                raise PixelLabError("Grupo perdeu seu UUID; conferir antes de novas cobranças.")
            response = client.animate(
                cid, name=name, description=by_name[name]["description"],
                direction=direction, frame_count=4,
                animation_group_id=group["id"] if group else None,
            )
            jobs = response.get("background_job_ids")
            if not isinstance(jobs, list) or len(jobs) != 1:
                raise PixelLabError("POST concluído com resposta inesperada; não repetir.")
            try:
                job = str(UUID(str(jobs[0])))
            except (ValueError, TypeError):
                raise PixelLabError("Identificador de job inválido; não repetir.") from None
            attempted.append({"motion": name, "direction": direction})
            save("job_submitted")
            client.poll([job], max_seconds=780)
            # A conclusão do job só conta se a biblioteca refletir a direção.
            confirmed = _groups(client.character(cid))
            if name not in confirmed or direction not in confirmed[name]["directions"]:
                raise PixelLabError("Job concluído, mas sprite ainda não aparece na biblioteca. Verificar manualmente.")
            finished.append({"motion": name, "direction": direction})
            save("progress")
            # espaçamento conservador entre gerações, sem reenvio de POST.
            if index < len(pending)-1:
                sleeper(1)
    except Exception:
        save("interrupted_review_before_retry")
        raise
    return save("completed" if len(first["pending"]) <= max_new else "partial_next_batch")


def main() -> None:
    p = argparse.ArgumentParser(description="PixelLab — animações da produtora")
    p.add_argument("--mode", choices=["plan", "generate"], default="plan")
    p.add_argument("--max-new", type=int, default=8)
    args = p.parse_args()
    token = os.getenv("PIXELLAB_API_TOKEN", "")
    fingerprint = os.getenv("PIXELLAB_TARGET_FINGERPRINT", "")
    if not fingerprint:
        p.exit(2, "PIXELLAB_TARGET_FINGERPRINT ausente.\n")
    try:
        client = PixelLabClient(token)
        cid = resolve_target(client, fingerprint)
        report = run(
            client, cid, read_catalog(), mode=args.mode, max_new=args.max_new,
            authorized=os.getenv("PIXELLAB_PRODUCTION_AUTHORIZED") == "true",
            public_report=os.getenv("PIXELLAB_PUBLIC_REPORT_AUTHORIZED") == "true",
        )
        print("PIXELLAB_PRODUCTION_STATUS=" + report["status"] +
              " completed=" + str(len(report["completed"])) +
              " before_missing=" + str(report["missing_before"]))
    except (ValueError, KeyError, OSError, PixelLabError) as exc:
        p.exit(1, "Produção PixelLab interrompida: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
