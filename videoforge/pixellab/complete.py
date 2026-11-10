"""Continuação sequencial e limitada das animações faltantes do PixelLab.

Não roda sozinha em push. Só workflow explicitamente autorizado pode chamá-la.
A cada rodada relê a API e não reenvia uma direção concluída.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .batch import MOTIONS, examine, plan as inspect_plan, run as run_batch
from .client import PixelLabClient, PixelLabError
from .launch import resolve_target


def write_report(output: Path, reports: list[dict], total_created: int,
                 *, result: str, missing: int | None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    safe = {
        "schema": "videoforge/pixellab-continuation/v1",
        "status": result,
        "created": total_created,
        "remaining": missing,
        "rounds": [
            {
                "index": i + 1,
                "created": len(r.get("completed", [])),
                "missing_before": r.get("missing_directions"),
                "status": r.get("result"),
                "completed": r.get("completed", []),
            }
            for i, r in enumerate(reports)
        ],
    }
    (output / "summary.json").write_text(
        json.dumps(safe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    location = os.environ.get("GITHUB_STEP_SUMMARY")
    if location:
        with Path(location).open("a", encoding="utf-8") as fp:
            fp.write(f"\n### Continuação PixelLab: {result}\n")
            fp.write(f"Novas animações concluídas: **{total_created}**\n")
            fp.write(f"Direções restantes: **{missing if missing is not None else 'desconhecido'}**\n")


def complete(client: PixelLabClient, target_id: str, *,
             max_total: int = 40, batch_size: int = 8,
             output: Path = Path("output/pixellab-complete")) -> dict:
    if not 1 <= max_total <= 48 or not 1 <= batch_size <= 8:
        raise ValueError("Limites de continuação inválidos.")
    reports: list[dict] = []
    created = 0
    missing = None
    try:
        while created < max_total:
            before = inspect_plan(client.character(target_id), MOTIONS)
            missing = before["missing"]
            if missing == 0:
                write_report(output, reports, created, result="completed", missing=0)
                return {"created": created, "missing": 0, "status": "completed"}
            next_size = min(batch_size, max_total - created, missing)
            r = run_batch(
                client, target_id, scope="all", mode="generate", max_new=next_size,
                allow_unknown=False, authorized=True, public_artifacts=True,
                export_zips=False, output=output / f"round-{len(reports)+1:02d}",
            )
            reports.append(r)
            created += len(r.get("completed", []))
            # Se API não atualizou suas direções apesar do job concluído,
            # impedir retry automático de POST e pedir verificação humana.
            after = inspect_plan(client.character(target_id), MOTIONS)
            missing = after["missing"]
            write_report(output, reports, created,
                         result="running", missing=missing)
            if missing >= before["missing"]:
                raise PixelLabError(
                    "API não refletiu direções novas; interrompido para evitar duplicatas."
                )
            if not r.get("completed"):
                raise PixelLabError(
                    "Nenhuma nova direção concluída; interrompido sem novas cobranças."
                )
        state = "completed" if missing == 0 else "max_total_reached"
        write_report(output, reports, created, result=state, missing=missing)
        return {"created": created, "missing": missing, "status": state}
    except Exception:
        write_report(output, reports, created,
                     result="interrupted_review_before_retry", missing=missing)
        raise


def main() -> None:
    fingerprint = os.getenv("PIXELLAB_TARGET_FINGERPRINT", "")
    if not fingerprint:
        raise SystemExit("Personagem não selecionado.")
    if os.getenv("PIXELLAB_GENERATION_AUTHORIZED") != "true":
        raise SystemExit("Sem autorização de custo para continuação.")
    try:
        api = PixelLabClient(os.getenv("PIXELLAB_API_TOKEN", ""))
        cid = resolve_target(api, fingerprint)
        report = complete(
            api, cid,
            max_total=int(os.getenv("PIXELLAB_MAX_TOTAL", "40")),
            batch_size=int(os.getenv("PIXELLAB_BATCH_SIZE", "8")),
        )
        print(
            "PIXELLAB_CONTINUATION=" + report["status"] +
            " created=" + str(report["created"]) +
            " remaining=" + str(report["missing"])
        )
    except (PixelLabError, ValueError, OSError) as exc:
        raise SystemExit("Continuação interrompida com segurança: " + str(exc)) from None


if __name__ == "__main__":
    main()
