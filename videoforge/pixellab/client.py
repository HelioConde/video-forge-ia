"""Cliente PixelLab REST v2 sem dependências externas.

POST de geração não é repetido automaticamente: isso evitaria cobranças duplicadas.
Nunca inclua token, payload completo ou IDs privados em logs públicos.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_ROOT = "https://api.pixellab.ai/v2"
FINAL = {"completed", "failed", "cancelled", "canceled"}


class PixelLabError(RuntimeError):
    """Erro sem conteúdo confidencial de requisições/respostas."""


class PixelLabClient:
    def __init__(self, token: str, *, timeout: int = 45):
        if not token.strip():
            raise PixelLabError("PIXELLAB_API_TOKEN não configurado no GitHub Secrets.")
        self.token = token.strip()
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict | None = None, *, binary: bool = False):
        if not path.startswith("/") or "//" in path or ".." in path or "?" in path:
            raise ValueError("Caminho de API inválido")
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(
            API_ROOT + path,
            data=body,
            method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/zip" if binary else "application/json",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                data = resp.read(40 * 1024 * 1024 + 1)
                if len(data) > 40 * 1024 * 1024:
                    raise PixelLabError("Resposta da API maior que 40 MB.")
                if binary:
                    if data[:4] != b"PK\x03\x04":
                        raise PixelLabError("Exportação não retornou um arquivo ZIP válido.")
                    return data
                try:
                    result = json.loads(data)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise PixelLabError("API retornou JSON inválido.") from exc
                if not isinstance(result, dict):
                    raise PixelLabError("Formato de resposta inesperado.")
                return result
        except HTTPError as exc:
            msg = {
                401: "Token PixelLab inválido ou expirado.",
                402: "Créditos PixelLab insuficientes.",
                403: "Sem acesso ao personagem solicitado.",
                404: "Personagem ou job não encontrado.",
                409: "Animação/direção já existente.",
                422: "Parâmetros recusados pela API PixelLab.",
                423: "Personagem ainda está sendo processado.",
                429: "Limite temporário de requisições PixelLab.",
            }.get(exc.code, "PixelLab indisponível ou resposta inesperada.")
            raise PixelLabError(f"HTTP {exc.code}: {msg}") from None
        except (TimeoutError, URLError) as exc:
            raise PixelLabError("Falha de conexão ou timeout com PixelLab. Não repetir POST às cegas.") from None

    def create(self, description: str, *, name: str, size: int, view: str, reference: dict | None):
        body = {
            "name": name,
            "description": description,
            "image_size": {"width": size, "height": size},
            "view": view,
            "template_id": "mannequin",
            "no_background": True,
            "enhance_prompt": False,
        }
        if reference is not None:
            body["reference_image"] = reference
        return self._request("POST", "/create-character-v3", body)

    def animate(self, character_id: str, *, name: str, description: str,
                direction: str, frame_count: int = 4):
        return self._request("POST", "/characters/animations", {
            "character_id": character_id,
            "animation_name": name,
            "action_description": description,
            "mode": "v3",
            "frame_count": frame_count,
            "directions": [direction],
            "keep_first_frame": False,
            "enhance_prompt": False,
        })

    def character(self, character_id: str):
        return self._request("GET", f"/characters/{character_id}")

    def job(self, job_id: str):
        return self._request("GET", f"/background-jobs/{job_id}")

    def poll(self, job_ids: list[str], *, max_seconds: int = 840, interval: int = 8,
             sleeper=time.sleep, clock=time.monotonic):
        if not job_ids or len(job_ids) > 8:
            raise PixelLabError("Número de jobs inválido.")
        deadline = clock() + max_seconds
        statuses = {}
        while clock() < deadline:
            for job_id in job_ids:
                if job_id in statuses:
                    continue
                current = self.job(job_id)
                status = current.get("status")
                if status in ("failed", "cancelled", "canceled"):
                    raise PixelLabError("Um job do PixelLab terminou com erro.")
                if status == "completed":
                    statuses[job_id] = current
                elif status not in ("queued", "processing", "pending"):
                    raise PixelLabError("Status desconhecido da API PixelLab.")
            if len(statuses) == len(job_ids):
                return statuses
            sleeper(interval)
        raise PixelLabError(
            "Tempo de espera encerrado. O job pode continuar no PixelLab; "
            "não dispare uma nova geração paga sem verificar o histórico."
        )

    def download(self, character_id: str, *, spritesheet: bool):
        kind = "spritesheet" if spritesheet else "zip"
        return self._request("GET", f"/characters/{character_id}/{kind}", binary=True)
