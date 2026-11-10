"""Lote PixelLab executável pelo GitHub Actions/ChatGPT Work.

Só cria direções comprovadamente ausentes. Nunca recria base, apaga animações,
imprime IDs privados ou repete automaticamente um POST pago.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import UUID

from .cli import DIRECTIONS, load_profile, parse_character_id
from .client import PixelLabClient, PixelLabError

MOTIONS = ("idle", "walk", "type", "sit", "talk", "wave")
ALIASES = {
    "idle": {"idle", "breathing", "idle breathing", "idle stance"},
    "walk": {"walk", "walking", "walking cycle", "walk cycle"},
    "type": {"type", "typing", "typing on keyboard"},
    "sit": {"sit", "sitting", "sit down"},
    "talk": {"talk", "talking", "speaking"},
    "wave": {"wave", "waving"},
}
MAX_NEW = 8


def _canonical_name(value: str) -> str | None:
    label = " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    matches = [key for key, synonyms in ALIASES.items() if label in synonyms]
    return matches[0] if len(matches) == 1 else None


def _extract_directions(group: dict) -> set[str]:
    values = group.get("directions")
    if not isinstance(values, list):
        raise PixelLabError("Grupo de animação sem lista de direções. Geração interrompida.")
    known = set()
    for entry in values:
        direction = entry if isinstance(entry, str) else (
            entry.get("direction") if isinstance(entry, dict) else None)
        if not isinstance(direction, str) or direction not in DIRECTIONS:
            raise PixelLabError("Direção desconhecida na API; não arriscar duplicação.")
        known.add(direction)
    return known


def examine(detail: dict) -> tuple[dict, int]:
    """Mapa de movimentos e grupos existentes; não adivinha IDs nem nomes desconhecidos."""
    groups = detail.get("animations")
    if not isinstance(groups, list):
        raise PixelLabError("API não forneceu grupos detalhados. Nenhuma geração autorizada.")
    catalog = {motion: [] for motion in MOTIONS}
    unknown = 0
    for group in groups:
        if not isinstance(group, dict):
            raise PixelLabError("Grupo malformado no PixelLab.")
        # Preferir display_name como nome editável, depois animation_type.
        label = group.get("display_name") or group.get("animation_name") or group.get("animation_type") or ""
        motion = _canonical_name(str(label))
        directions = _extract_directions(group)
        if motion is None:
            unknown += 1
            continue
        raw_id = group.get("animation_group_id") or group.get("id")
        group_id = None
        if raw_id:
            try:
                group_id = str(UUID(str(raw_id)))
            except (ValueError, TypeError):
                raise PixelLabError("ID de grupo existente inválido; geração interrompida.")
        catalog[motion].append({"directions": directions, "group_id": group_id})
    return catalog, unknown


def plan(detail: dict, motions: tuple[str, ...], *, allow_unknown: bool = False) -> dict:
    catalog, unknown = examine(detail)
    tasks = []
    existing = 0
    for motion in motions:
        groups = catalog[motion]
        if len(groups) > 1:
            raise PixelLabError(
                "Mais de um grupo para o movimento " + motion +
                ". Revise no PixelLab antes de gerar."
            )
        group = groups[0] if groups else None
        used = group["directions"] if group else set()
        existing += len(used)
        for direction in DIRECTIONS:
            if direction in used:
                continue
            # Não crie um grupo duplicado se um grupo de nome desconhecido puder
            # ser a animação procurada. Liberação explícita apenas após auditoria.
            if unknown and not groups and not allow_unknown:
                raise PixelLabError(
                    "Existem grupos de nomes desconhecidos; não é seguro criar " +
                    motion + " sem revisar. Use a liberação explícita somente após auditoria."
                )
            if group and not group["group_id"]:
                raise PixelLabError(
                    "Animação " + motion +
                    " existe parcialmente mas o ID do grupo não veio da API."
                )
            tasks.append({
                "motion": motion,
                "direction": direction,
                "group_id": group["group_id"] if group else None
            })
    return {
        "existing": existing,
        "missing": len(tasks),
        "unknown_groups": unknown,
        "tasks": tasks,
    }


def _public_report(character: str, mode: str, scope: str, planned: dict,
                   limit: int, *, started: list[dict], completed: list[dict],
                   result: str) -> dict:
    return {
        "schema": "videoforge/pixellab-batch/v1",
        "character": character,
        "mode": mode,
        "scope": scope,
        "max_new": limit,
        "existing_directions": planned["existing"],
        "missing_directions": planned["missing"],
        "unclassified_groups": planned["unknown_groups"],
        "selected": [
            {"motion": x["motion"], "direction": x["direction"]}
            for x in planned["tasks"][:limit]
        ],
        "submitted": started[:],
        "completed": completed[:],
        "result": result,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        lines = [
            "## PixelLab — geração em lote",
            "",
            "Modo: **" + report["mode"] + "**",
            "Direções já existentes: **" + str(report["existing_directions"]) + "**",
            "Direções faltantes: **" + str(report["missing_directions"]) + "**",
            "Novas iniciadas: **" + str(len(report["submitted"])) + "**",
            "Novas concluídas: **" + str(len(report["completed"])) + "**",
            "",
            "Nenhum token, ID do personagem ou ID dos jobs foi exportado.",
            "",
        ]
        with Path(summary_file).open("a", encoding="utf-8") as output:
            output.write("\n".join(lines))


def run(client: PixelLabClient, character_id: str, *,
        scope: str = "all", mode: str = "plan", max_new: int = 4,
        allow_unknown: bool = False, authorized: bool = False,
        public_artifacts: bool = False,
        export_zips: bool = False,
        output: Path = Path("output/pixellab-batch")) -> dict:
    if scope not in (*MOTIONS, "all"):
        raise ValueError("Movimento inválido.")
    if mode not in ("plan", "generate"):
        raise ValueError("Modo inválido.")
    if not isinstance(max_new, int) or not 1 <= max_new <= MAX_NEW:
        raise ValueError("Máximo permitido: de 1 a 8 novas direções por execução.")
    cid = parse_character_id(character_id)
    motions = MOTIONS if scope == "all" else (scope,)
    profile = load_profile("alex")
    detail = client.character(cid)
    planned = plan(detail, motions, allow_unknown=allow_unknown)
    started: list[dict] = []
    completed: list[dict] = []
    output.mkdir(parents=True, exist_ok=True)
    report_file = output / "report.json"

    def save(status: str) -> dict:
        report = _public_report("alex", mode, scope, planned, max_new,
                                started=started, completed=completed, result=status)
        _write_report(report_file, report)
        return report

    save("planned")
    if mode == "plan":
        return save("planned_only")
    if not authorized or not public_artifacts:
        raise PixelLabError("Geração em lote exige autorização explícita de custo e artefatos públicos.")

    # O limite e a seleção são calculados antes do primeiro POST.
    # O workflow usa um único grupo de concorrência para não gerar a mesma direção
    # em duas execuções ao mesmo tempo.
    group_ids = {}
    try:
        for item in planned["tasks"][:max_new]:
            motion, direction = item["motion"], item["direction"]
            # Revalidar antes de cada cobrança: pode haver atraso de persistência
            # ou animações concluídas por outras execuções.
            fresh = client.character(cid)
            checked = plan(fresh, (motion,), allow_unknown=allow_unknown)
            if not any(x["direction"] == direction for x in checked["tasks"]):
                continue
            # Reutilizar o ID de grupo criado nesta mesma execução, quando aplicável.
            remote, _ = examine(fresh)
            available = remote[motion]
            group_id = (available[0]["group_id"] if available else
                        group_ids.get(motion))
            # Não criar novo grupo caso não seja possível anexar ao existente.
            if available and not group_id:
                raise PixelLabError("Grupo existente não pode ser estendido com segurança.")
            response = client.animate(
                cid, name=motion, description=profile["motions"][motion],
                direction=direction, frame_count=4, animation_group_id=group_id,
            )
            jobs = response.get("background_job_ids")
            if not isinstance(jobs, list) or len(jobs) != 1:
                raise PixelLabError("Resposta da geração não contém exatamente um job.")
            job_id = parse_character_id(jobs[0])
            # Nunca divulgar o UUID privado no report/Actions público.
            created = response.get("animation_group_id")
            if created:
                group_ids[motion] = parse_character_id(created)
            started.append({"motion": motion, "direction": direction})
            save("job_submitted")
            client.poll([job_id], max_seconds=780)
            completed.append({"motion": motion, "direction": direction})
            save("job_completed")
    except Exception:
        save("interrupted_check_jobs_before_retry")
        raise

    if export_zips:
        # Os ZIPs incluem metadados/IDs: só exportar com consentimento público explícito.
        (output / "character-frames.zip").write_bytes(
            client.download(cid, spritesheet=False)
        )
        (output / "spritesheet.zip").write_bytes(
            client.download(cid, spritesheet=True)
        )
    return save("completed")


def main() -> None:
    parser = argparse.ArgumentParser(description="PixelLab: lote idempotente para Work")
    parser.add_argument("--mode", choices=("plan", "generate"), default="plan")
    parser.add_argument("--scope", choices=("all", *MOTIONS), default="all")
    parser.add_argument("--max-new", type=int, default=4)
    parser.add_argument("--allow-unknown", action="store_true")
    parser.add_argument("--authorize-cost", action="store_true")
    parser.add_argument("--public-artifacts", action="store_true")
    parser.add_argument("--export-zips", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("PIXELLAB_API_TOKEN", "")
    character_id = os.environ.get("PIXELLAB_CHARACTER_ID", "")
    if not character_id:
        parser.exit(2, "PIXELLAB_CHARACTER_ID não configurado. Escolha uma base no GitHub Secrets.\n")
    try:
        result = run(
            PixelLabClient(token), character_id,
            scope=args.scope, mode=args.mode, max_new=args.max_new,
            allow_unknown=args.allow_unknown, authorized=args.authorize_cost,
            public_artifacts=args.public_artifacts, export_zips=args.export_zips,
        )
    except (PixelLabError, ValueError, KeyError, OSError) as exc:
        parser.exit(1, "Lote interrompido: " + str(exc) + "\n")
    print("PIXELLAB_BATCH_STATUS=" + result["result"])
    print("Direções existentes:", result["existing_directions"],
          "| faltantes:", result["missing_directions"],
          "| concluídas nesta execução:", len(result["completed"]))


if __name__ == "__main__":
    main()
