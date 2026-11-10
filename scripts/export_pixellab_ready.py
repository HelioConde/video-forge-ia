"""Exportação por GET com tratamento explícito da indisponibilidade HTTP 423.

O PixelLab bloqueia /characters/{id}/zip enquanto gera animações. Nesse caso,
adiar a sincronização é correto; o workflow_run a repetirá após a geração.
Nenhum POST, token, UUID ou arquivo privado é publicado.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from videoforge.pixellab.client import PixelLabClient, PixelLabError
from videoforge.pixellab.launch import resolve_target


def export_when_ready(client: PixelLabClient, cid: str, dest: Path) -> str:
    try:
        payload = client.download(cid, spritesheet=False)
    except PixelLabError as error:
        if str(error).startswith("HTTP 423:"):
            return "source_processing"
        raise
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload)
    return "exported"


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    args=parser.parse_args()
    cli=PixelLabClient(os.environ.get("PIXELLAB_API_TOKEN",""))
    cid=resolve_target(cli,os.environ.get("PIXELLAB_TARGET_FINGERPRINT",""))
    status=export_when_ready(cli,cid,args.source)
    print("PIXELLAB_EXPORT_READY="+status)
    if status=="source_processing":
        info={"schema":"videoforge/pixellab-production-ingest-summary/v1",
              "status":"source_processing",
              "reason":"PixelLab HTTP 423: geração do personagem em andamento",
              "received_motions":0,
              "note":"Esta execução não alterou sprites; importação será repetida no fim do lote."}
        file=Path("output/pixellab-production/receive-summary.json")
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text(json.dumps(info,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        summary=os.getenv("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary,"a",encoding="utf-8") as f:
                f.write("## Alex ainda está em geração no PixelLab (HTTP 423)\n\n")
                f.write("Nenhum ZIP disponível para exportação; não repetir POST nem marcar sprites como concluídos.\n")


if __name__=="__main__":
    main()
