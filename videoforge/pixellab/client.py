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
from urllib.parse import urlencode


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

    def _request(self, method: str, path: str, payload: dict | None = None, *,
                 binary: bool = False, query: dict[str, int] | None = None):
        if not path.startswith("/") or "//" in path or ".." in path or "?" in path:
            raise ValueError("Caminho de API inválido")
        if query is not None:
            if method != "GET" or not isinstance(query, dict) or set(query) - {"limit", "offset"}:
                raise ValueError("Consulta de API inválida")
            if not all(type(v) is int and 0 <= v <= 1000 for v in query.values()):
                raise ValueError("Paginação fora dos limites permitidos")
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        url = API_ROOT + path + ("?" + urlencode(query) if query else "")
        req = Request(
            url,
            data=body,
            method=method,
            headers={
                # ZIPs não exigem autenticação. Nunca encaminhar Bearer para redirects de storage.
                **({} if binary else {"Authorization": "Bearer " + self.token}),
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
                direction: str, frame_count: int = 4,
                animation_group_id: str | None = None):
        return self._request("POST", "/characters/animations", {
            "character_id": character_id,
            **({"animation_group_id": animation_group_id} if animation_group_id else {}),
            "animation_name": name,
            "action_description": description,
            "mode": "v3",
            "frame_count": frame_count,
            "directions": [direction],
            "keep_first_frame": False,
            "enhance_prompt": False,
        })

    def characters(self):
        """Inventário de conta; seleção automática apenas quando não é ambígua."""
        return self._request("GET", "/characters")

    def state(self, character_id: str, *, name: str, description: str):
        """Variação de pose: aplica a mesma mudança em todas as direções."""
        return self._request("POST", "/create-character-state", {
            "character_id": character_id,
            "edit_description": description,
            "state_name": name,
            "use_color_palette_from_reference": True,
            "no_background": True,
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


    def download_object_spritesheet(self, object_id: str) -> bytes:
        """GET autenticado do ZIP de objeto; remove Authorization em redirects.

        /objects/{id}/spritesheet precisa Bearer. Redirecionamentos para o
        storage são seguidos SEM token. Nunca gera/edita objetos.
        """
        from urllib.request import build_opener, HTTPRedirectHandler
        from urllib.parse import urlparse
        from uuid import UUID

        try:
            oid = str(UUID(object_id))
        except (ValueError, TypeError):
            raise PixelLabError("ID de objeto inválido.") from None

        class StorageRedirect(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                target = urlparse(newurl)
                host = (target.hostname or "").lower()
                allowed = ("pixellab.ai", "cloudfront.net", "amazonaws.com",
                           "googleapis.com", "r2.dev")
                if target.scheme != "https" or not any(
                    host == domain or host.endswith("." + domain) for domain in allowed
                ):
                    raise PixelLabError("Redirecionamento de exportação não autorizado.")
                # Nunca transportar token ao domínio de armazenamento.
                return Request(newurl, method="GET", headers={"Accept": "application/zip"})

        url = API_ROOT + f"/objects/{oid}/spritesheet"
        req = Request(url, method="GET", headers={
            "Authorization": "Bearer " + self.token,
            "Accept": "application/zip",
        })
        try:
            with build_opener(StorageRedirect).open(req, timeout=self.timeout) as response:
                payload = response.read(40 * 1024 * 1024 + 1)
            if len(payload) > 40 * 1024 * 1024 or payload[:4] != b"PK\x03\x04":
                raise PixelLabError("Exportação ZIP de objeto inválida ou muito grande.")
            return payload
        except HTTPError as exc:
            raise PixelLabError(f"Exportação de objeto indisponível (HTTP {exc.code}).") from None
        except (TimeoutError, URLError, OSError):
            raise PixelLabError("Falha ao exportar objeto; nenhuma geração foi iniciada.") from None
