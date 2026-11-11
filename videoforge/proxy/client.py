"""Cliente backend para TODAS as 22 rotas do chatgpt-codex-proxy.

Nunca importar este modulo no GitHub Pages. Nenhuma chamada ocorre no import,
na construcao do cliente ou na listagem de capacidades. Requisicoes gerativas
exigem chamada explicita. Tokens sao carregados somente no backend.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from urllib import error, parse, request
from urllib.parse import urlsplit

MAX_RESPONSE_BYTES = 40 * 1024 * 1024
MAX_REQUEST_BYTES = 40 * 1024 * 1024

# Contrato verificado no commit upstream fixado pelo AutoEditorVideo.
ENDPOINTS = {
    "health_live": ("GET", "/health/live"),
    "health": ("GET", "/health"),
    "models": ("GET", "/v1/models"),
    "model": ("GET", "/v1/models/:model_id"),
    "completions": ("POST", "/v1/completions"),
    "chat": ("POST", "/v1/chat/completions"),
    "responses": ("POST", "/v1/responses"),
    "responses_websocket": ("GET", "/v1/responses"),
    "compact": ("POST", "/v1/responses/compact"),
    "images_generate": ("POST", "/v1/images/generations"),
    "images_edit": ("POST", "/v1/images/edits"),
    "messages": ("POST", "/v1/messages"),
    "count_tokens": ("POST", "/v1/messages/count_tokens"),
    "accounts": ("GET", "/admin/accounts"),
    "device_login_start": ("POST", "/admin/accounts/device-login/start"),
    "device_login_status": ("GET", "/admin/accounts/device-login/:login_id"),
    "account_delete": ("DELETE", "/admin/accounts/:account_id"),
    "account_patch": ("PATCH", "/admin/accounts/:account_id"),
    "account_usage": ("GET", "/admin/accounts/:account_id/usage"),
    "account_refresh": ("POST", "/admin/accounts/:account_id/refresh"),
    "rotation_get": ("GET", "/admin/rotation"),
    "rotation_put": ("PUT", "/admin/rotation"),
}
READ_ONLY = frozenset({
    "health_live", "health", "models", "model", "accounts",
    "device_login_status", "account_usage", "rotation_get",
})


class ProxyError(RuntimeError):
    """Erro publicavel: nunca transporta corpo upstream, cookies ou tokens."""


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _validated_url(value: str) -> str:
    value = value.strip().rstrip("/")
    u = urlsplit(value)
    if not u.netloc or u.username or u.password or u.path not in ("", "/") or u.query or u.fragment:
        raise ValueError("VIDEOFORGE_PROXY_URL invalida")
    if u.scheme == "https":
        return value
    if u.scheme == "http" and u.hostname in {"localhost", "127.0.0.1", "::1"}:
        return value
    raise ValueError("Proxy sem TLS so e permitido em localhost")


def _segment(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256 or any(c in value for c in "\r\n"):
        raise ValueError("ID invalido")
    return parse.quote(value, safe="")


class ProxyClient:
    def __init__(self, *, base_url: str | None = None,
                 api_key: str | None = None, timeout: float = 30,
                 opener=None):
        self.base_url = _validated_url(
            base_url or os.getenv("VIDEOFORGE_PROXY_URL", "http://127.0.0.1:8080")
        )
        self._key = api_key if api_key is not None else os.getenv("PROXY_API_KEY", "")
        if timeout <= 0 or timeout > 3600:
            raise ValueError("Timeout fora do intervalo permitido")
        self.timeout = timeout
        self._open = opener or request.build_opener(_NoRedirect()).open

    @staticmethod
    def capabilities() -> dict:
        """Lista recursos sem conexao ou credenciais."""
        return {key: {"method": method, "path": path, "read_only": key in READ_ONLY}
                for key, (method, path) in ENDPOINTS.items()}

    def _headers(self, *, authorized: bool = True, anthropic: bool = False) -> dict:
        h = {"Accept": "application/json", "User-Agent": "VideoForgeAI-proxy-client/1"}
        if authorized:
            if not isinstance(self._key, str) or len(self._key.strip()) < 15:
                raise ProxyError("PROXY_API_KEY ausente ou invalida no backend")
            h["Authorization"] = "Bearer " + self._key.strip()
        if anthropic:
            h["Anthropic-Version"] = "2023-06-01"
        return h

    def _url(self, path: str) -> str:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Caminho de endpoint invalido")
        return self.base_url + path

    def _send(self, method: str, path: str, data=None, *,
              authorized: bool = True, anthropic: bool = False,
              stream: bool = False):
        headers = self._headers(authorized=authorized, anthropic=anthropic)
        payload = None
        if data is not None:
            try:
                payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            except (TypeError, ValueError):
                raise ProxyError("Payload JSON invalido") from None
            if len(payload) > MAX_REQUEST_BYTES:
                raise ProxyError("Payload excede limite local")
            headers["Content-Type"] = "application/json"
        if stream:
            headers["Accept"] = "text/event-stream"
        req = request.Request(self._url(path), data=payload, headers=headers, method=method)
        try:
            return self._open(req, timeout=self.timeout)
        except error.HTTPError as exc:
            # Nunca incluir a mensagem ou corpo do provedor nos logs publicos.
            raise ProxyError("Codex Proxy HTTP " + str(exc.code)) from None
        except (error.URLError, OSError, TimeoutError):
            raise ProxyError("Codex Proxy indisponivel") from None

    def _json(self, method: str, path: str, data=None, **kwargs):
        with self._send(method, path, data, **kwargs) as res:
            if res.status == 204:
                return None
            body = res.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise ProxyError("Resposta excede limite local")
            try:
                return json.loads(body)
            except (ValueError, TypeError):
                raise ProxyError("Resposta JSON invalida do proxy") from None

    def _events(self, method: str, path: str, payload: dict, *, anthropic: bool = False):
        """Entrega eventos SSE sem guardar stream inteiro na memoria."""
        with self._send(method, path, payload, anthropic=anthropic, stream=True) as res:
            total = 0
            event = {"event": "message", "data": []}
            for raw in res:
                total += len(raw)
                if total > MAX_RESPONSE_BYTES:
                    raise ProxyError("Stream excede limite local")
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if not line:
                    if event["data"]:
                        value = "\n".join(event["data"])
                        if value == "[DONE]":
                            return
                        try:
                            decoded = json.loads(value)
                        except ValueError:
                            decoded = value
                        yield {"event": event["event"], "data": decoded}
                    event = {"event": "message", "data": []}
                elif line.startswith("event:"):
                    event["event"] = line[6:].strip()
                elif line.startswith("data:"):
                    event["data"].append(line[5:].lstrip())
            if event["data"]:
                yield {"event": event["event"], "data": "\n".join(event["data"])}

    # Diagnostico e catalogo
    def health_live(self): return self._json("GET", "/health/live", authorized=False)
    def health(self): return self._json("GET", "/health")
    def models(self, *, client_version: str | None = None):
        qs = "?"+parse.urlencode({"client_version": client_version}) if client_version else ""
        return self._json("GET", "/v1/models"+qs)
    def model(self, model_id: str): return self._json("GET", "/v1/models/"+_segment(model_id))

    # Texto, raciocinio, ferramentas e formato estruturado
    def completions(self, body: dict): return self._json("POST", "/v1/completions", body)
    def chat(self, body: dict): return self._json("POST", "/v1/chat/completions", body)
    def responses(self, body: dict): return self._json("POST", "/v1/responses", body)
    def compact(self, body: dict): return self._json("POST", "/v1/responses/compact", body)
    def chat_stream(self, body: dict):
        return self._events("POST", "/v1/chat/completions", {**body, "stream": True})
    def responses_stream(self, body: dict):
        return self._events("POST", "/v1/responses", {**body, "stream": True})

    # Imagem nativa: geracao ou edicao com referencias e mascaras JSON.
    def images_generate(self, body: dict): return self._json("POST", "/v1/images/generations", body)
    def images_edit(self, body: dict): return self._json("POST", "/v1/images/edits", body)
    def images_generate_stream(self, body: dict):
        return self._events("POST", "/v1/images/generations", {**body, "stream": True})
    def images_edit_stream(self, body: dict):
        return self._events("POST", "/v1/images/edits", {**body, "stream": True})

    @staticmethod
    def _local_image_data_url(path: str | Path, *, mask: bool = False) -> str:
        """Somente arquivo local aprovado; sem baixar URL arbitraria."""
        f = Path(path)
        if not f.is_file() or f.is_symlink():
            raise ProxyError("Referencia local inexistente ou insegura")
        if f.stat().st_size > 18_000_000:
            raise ProxyError("Referencia local excede 18MB")
        blob = f.read_bytes()
        if blob.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
            mime = "image/png"
        elif not mask and blob.startswith(b"\\xff\\xd8\\xff"):
            mime = "image/jpeg"
        elif not mask and blob.startswith(b"RIFF") and blob[8:12] == b"WEBP":
            mime = "image/webp"
        else:
            raise ProxyError("Formato de referencia invalido")
        return "data:"+mime+";base64,"+base64.b64encode(blob).decode("ascii")

    def images_edit_files(self, *, prompt: str, images: list[str | Path],
                          model: str = "gpt-image-2",
                          mask: str | Path | None = None, **options):
        """Editar PNG/JPEG/WebP locais via JSON /v1/images/edits (sem multipart)."""
        if not isinstance(prompt, str) or not prompt.strip() or not 1 <= len(images) <= 8:
            raise ValueError("Prompt e 1-8 referencias sao obrigatorios")
        forbidden = {"prompt", "model", "images", "mask", "stream"}
        if forbidden & set(options):
            raise ValueError("Opcoes reservadas nao podem ser redefinidas")
        payload = {"model": model, "prompt": prompt,
                   "images": [{"image_url": self._local_image_data_url(p)} for p in images],
                   **options}
        if mask is not None:
            payload["mask"] = {"image_url": self._local_image_data_url(mask, mask=True)}
        return self.images_edit(payload)

    # Compatibilidade Anthropic para clientes locais e agentes.
    def messages(self, body: dict):
        return self._json("POST", "/v1/messages", body, anthropic=True)
    def count_tokens(self, body: dict):
        return self._json("POST", "/v1/messages/count_tokens", body, anthropic=True)
    def messages_stream(self, body: dict):
        return self._events("POST", "/v1/messages", {**body, "stream": True}, anthropic=True)

    # WebSocket: opcional; nao pode funcionar no Pages estatico.
    def responses_websocket(self):
        """Retorna conexao WebSocket backend; requer websockets>=14 instalado."""
        try:
            from websockets.sync.client import connect
        except ImportError:
            raise ProxyError("Instale websockets>=14 no backend para Responses WebSocket") from None
        headers = self._headers()
        ws_url = ("wss://" if self.base_url.startswith("https://") else "ws://") + self.base_url.split("://", 1)[1] + "/v1/responses"
        try:
            return connect(ws_url, additional_headers=headers, open_timeout=self.timeout)
        except Exception:
            raise ProxyError("Falha ao conectar ao WebSocket do proxy") from None

    # Administracao — chamadas modificadoras somente quando invocadas.
    def accounts(self): return self._json("GET", "/admin/accounts")
    def device_login_start(self): return self._json("POST", "/admin/accounts/device-login/start", {})
    def device_login_status(self, login_id: str):
        return self._json("GET", "/admin/accounts/device-login/"+_segment(login_id))
    def account_delete(self, account_id: str):
        return self._json("DELETE", "/admin/accounts/"+_segment(account_id))
    def account_patch(self, account_id: str, *, status: str | None = None, label: str | None = None):
        if status is not None and status not in ("active", "disabled"):
            raise ValueError("Status de conta invalido")
        if status is None and label is None:
            raise ValueError("Indique status ou label")
        return self._json("PATCH", "/admin/accounts/"+_segment(account_id),
                          {k:v for k,v in {"status":status,"label":label}.items() if v is not None})
    def account_usage(self, account_id: str, *, cached: bool = True):
        qs = "?cached=true" if cached else ""
        return self._json("GET", "/admin/accounts/"+_segment(account_id)+"/usage"+qs)
    def account_refresh(self, account_id: str):
        return self._json("POST", "/admin/accounts/"+_segment(account_id)+"/refresh", {})
    def rotation_get(self): return self._json("GET", "/admin/rotation")
    def rotation_put(self, strategy: str):
        if strategy not in ("least_used", "round_robin", "sticky"):
            raise ValueError("Estrategia de rotacao invalida")
        return self._json("PUT", "/admin/rotation", {"strategy": strategy})
