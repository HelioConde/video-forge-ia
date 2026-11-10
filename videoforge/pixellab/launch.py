"""Disparo controlado de lote para o personagem PixelLab identificado pelo proprietário.

O código compara SHA256 dos IDs devolvidos pela API, sem armazenar ou expor o
UUID do personagem. Não há consultas à conta de outros usuários.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re

from .batch import run
from .client import PixelLabClient, PixelLabError
from .cli import parse_character_id

FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


def resolve_target(client: PixelLabClient, fingerprint: str) -> str:
    if not FINGERPRINT.fullmatch(fingerprint):
        raise PixelLabError("Impressão digital de personagem inválida.")
    page = client.characters()
    characters = page.get("characters")
    total = page.get("total")
    if not isinstance(characters, list) or not isinstance(total, int):
        raise PixelLabError("Biblioteca PixelLab não retornou lista completa.")
    if len(characters) != total:
        raise PixelLabError("Biblioteca paginada ou incompleta; não escolher base.")
    found = []
    for c in characters:
        if not isinstance(c, dict):
            raise PixelLabError("Registro de personagem inválido.")
        cid = parse_character_id(c.get("id"))
        digest = hashlib.sha256(cid.encode("utf-8")).hexdigest()
        if digest == fingerprint:
            found.append(cid)
    if len(found) != 1:
        raise PixelLabError(
            "O personagem selecionado não foi identificado unicamente no PixelLab. "
            "Nenhuma geração será iniciada."
        )
    return found[0]


def main() -> None:
    fingerprint = os.environ.get("PIXELLAB_TARGET_FINGERPRINT", "")
    if not fingerprint:
        raise SystemExit("Impressão digital do personagem não configurada.")
    mode = os.environ.get("PIXELLAB_LAUNCH_MODE", "plan")
    try:
        client = PixelLabClient(os.environ.get("PIXELLAB_API_TOKEN", ""))
        character_id = resolve_target(client, fingerprint)
        report = run(
            client, character_id, scope=os.environ.get("PIXELLAB_SCOPE", "all"),
            mode=mode,
            max_new=int(os.environ.get("PIXELLAB_MAX_NEW", "4")),
            authorized=os.environ.get("PIXELLAB_GENERATION_AUTHORIZED") == "true",
            public_artifacts=os.environ.get("PIXELLAB_PUBLIC_REPORT_AUTHORIZED") == "true",
            # Nunca publicar os sprites/IDs nos artefatos públicos deste disparo.
            export_zips=False,
            output=Path("output/pixellab-batch"),
        )
        print(
            "PIXELLAB_LAUNCH_STATUS=" + report["result"],
            "existing=" + str(report["existing_directions"]),
            "missing=" + str(report["missing_directions"]),
            "completed=" + str(len(report["completed"])),
        )
    except (ValueError, PixelLabError) as exc:
        raise SystemExit("Disparo PixelLab interrompido com segurança: " + str(exc)) from None


if __name__ == "__main__":
    main()
