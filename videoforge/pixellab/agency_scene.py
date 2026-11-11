"""Geração segura da fachada e do piso unificados da agência via PixelLab v2.

Utiliza o PixelLabClient já existente, uma referência visual local e uma
única geração Pro. Produção/agents permanecem desacoplados da arte de fundo.
Não altera o GitHub Pages sem revisão humana do PNG gerado.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import time
from uuid import UUID

from .client import PixelLabClient, PixelLabError

PLAN = Path("cenarios/escritorio/agencia-unificada.json")
REPORT_DIR = Path("output/pixellab-agency")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 10 * 1024 * 1024


def png_dimensions(image: bytes) -> tuple[int, int]:
    if len(image) < 24 or not image.startswith(PNG_SIGNATURE) or image[12:16] != b"IHDR":
        raise ValueError("Referência/resultado precisa ser PNG válido.")
    width, height = struct.unpack(">II", image[16:24])
    if not (16 <= width <= 2048 and 16 <= height <= 2048):
        raise ValueError("PNG com dimensões inesperadas.")
    return width, height


def read_plan(path: Path = PLAN) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("endpoint") != "/generate-image-v2":
        raise ValueError("Endpoint não autorizado para o cenário.")
    size = plan["image_size"]
    if (size["width"], size["height"]) != (688, 384):
        raise ValueError("Resolução PixelLab esperada: 688x384.")
    if len(plan["description"]) > 2000:
        raise ValueError("Prompt excede limite do PixelLab.")
    if Path(plan["reference"]).is_absolute() or ".." in Path(plan["reference"]).parts:
        raise ValueError("Caminho de referência inválido.")
    return plan


def reference_bytes(plan: dict) -> bytes:
    image = Path(plan["reference"]).read_bytes()
    if len(image) > MAX_PNG_BYTES:
        raise ValueError("Imagem de referência grande demais.")
    if hashlib.sha256(image).hexdigest() != plan["reference_sha256"]:
        raise ValueError("Imagem de referência alterada; revisar antes de gerar.")
    if dict(zip(("width", "height"), png_dimensions(image))) != plan["reference_size"]:
        raise ValueError("Dimensões da referência diferentes do plano.")
    return image


def make_payload(plan: dict, image: bytes) -> dict:
    size = plan["reference_size"]
    ref = {"image": {"base64": "data:image/png;base64," + base64.b64encode(image).decode("ascii")},
           "size": size}
    return {"description": plan["description"],
            "image_size": plan["image_size"],
            "reference_images": [{**ref, "usage_description": plan["usage_description"]}],
            "style_image": ref,
            "no_background": False}


def _image_from_job(result: dict) -> bytes:
    response = result.get("last_response") or {}
    if not isinstance(response, dict):
        raise PixelLabError("Resultado do PixelLab não contém imagem utilizável.")
    candidates = response.get("images")
    if not isinstance(candidates, list) or not candidates:
        candidates = [response.get("image")]
    item = candidates[0]
    if isinstance(item, dict):
        item = item.get("base64") or (item.get("image") or {}).get("base64")
    if not isinstance(item, str):
        raise PixelLabError("PixelLab terminou sem PNG; conferir histórico do job.")
    item = item.removeprefix("data:image/png;base64,")
    try:
        raw = base64.b64decode(item, validate=True)
    except (ValueError, base64.binascii.Error):
        raise PixelLabError("PixelLab devolveu PNG codificado incorretamente.") from None
    if not raw or len(raw) > MAX_PNG_BYTES:
        raise PixelLabError("Tamanho do PNG fora dos limites.")
    png_dimensions(raw)
    return raw


def save_report(path: Path, *, mode: str, state: str, dimensions: tuple[int, int] | None = None) -> dict:
    report = {"source": "pixellab-v2", "scene": "agencia-unificada",
              "mode": mode, "state": state, "new_paid_requests": 0 if mode == "plan" else 1,
              "requires_visual_approval": True}
    if dimensions:
        report["size"] = {"width": dimensions[0], "height": dimensions[1]}
    path.mkdir(parents=True, exist_ok=True)
    (path / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def run(client: PixelLabClient | None = None, *, mode: str = "plan",
        authorized: bool = False, public_artifact_authorized: bool = False,
        output: Path = REPORT_DIR, plan_path: Path = PLAN,
        sleeper=time.sleep, clock=time.monotonic, timeout_seconds: int = 900) -> dict:
    if mode not in {"plan", "generate"}:
        raise ValueError("Modo deve ser plan ou generate.")
    plan = read_plan(plan_path)
    image = reference_bytes(plan)
    payload = make_payload(plan, image)
    if mode == "plan":
        return save_report(output, mode=mode, state="ready", dimensions=png_dimensions(image))
    if not authorized or not public_artifact_authorized:
        raise PixelLabError("Geração bloqueada: confirmar custo e visibilidade do artifact.")
    if client is None:
        client = PixelLabClient(os.environ.get("PIXELLAB_API_TOKEN", ""))
    # Uma única chamada POST paga. Nunca repetir automaticamente em timeout,
    # erro 409 ou resposta sem ID; investigar a execução anterior primeiro.
    answer = client._request("POST", "/generate-image-v2", payload)
    job_id = answer.get("background_job_id")
    try:
        job_id = str(UUID(job_id))
    except (TypeError, ValueError, AttributeError):
        raise PixelLabError("POST recebido sem ID válido; não reenviar geração.") from None
    save_report(output, mode=mode, state="submitted")
    deadline = clock() + timeout_seconds
    while clock() < deadline:
        data = client._request("GET", "/background-jobs/" + job_id)
        status = data.get("status")
        if status == "completed":
            png = _image_from_job(data)
            (output / "scene.png").write_bytes(png)
            return save_report(output, mode=mode, state="generated_preview",
                               dimensions=png_dimensions(png))
        if status in {"failed", "cancelled", "canceled"}:
            raise PixelLabError("Geração rejeitada/falhou; revisar antes de novo POST.")
        if status not in {"queued", "pending", "processing", "generating", "in_progress"}:
            raise PixelLabError("Estado desconhecido; revisar job antes de outro POST.")
        sleeper(8)
    raise PixelLabError("A geração pode continuar no PixelLab; não repetir POST antes de consultar jobs.")


def main() -> None:
    parser = argparse.ArgumentParser(description="PixelLab - Agência única VideoForge")
    parser.add_argument("--mode", choices=["plan", "generate"], default="plan")
    args = parser.parse_args()
    try:
        report = run(mode=args.mode,
                     authorized=os.environ.get("PIXELLAB_SCENE_AUTHORIZED") == "true",
                     public_artifact_authorized=os.environ.get("PIXELLAB_SCENE_PUBLIC_ARTIFACT") == "true")
        print("PIXELLAB_AGENCY_STATE=" + report["state"])
    except (OSError, ValueError, KeyError, PixelLabError) as exc:
        raise SystemExit("PixelLab agência interrompido: " + str(exc)) from None


if __name__ == "__main__":
    main()
