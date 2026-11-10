"""Diagnóstico somente leitura da integração PixelLab.

Apenas GET /balance e GET /characters. Não gera mídia, não altera conta,
não imprime saldos, prompts, personagens, IDs ou valores de Secrets.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Any

from .client import PixelLabClient, PixelLabError


def verify_connection(token: str, client_factory: Callable[[str], Any] = PixelLabClient) -> str:
    if not token or not token.strip():
        return "NOT_CONFIGURED"
    try:
        client = client_factory(token)
        balance = client._request("GET", "/balance")
        if not isinstance(balance.get("credits"), dict):
            return "UNEXPECTED_BALANCE_RESPONSE"
        library = client.characters()
        if not isinstance(library.get("characters"), list):
            return "UNEXPECTED_LIBRARY_RESPONSE"
        return "CONNECTED"
    except PixelLabError as exc:
        message = str(exc)
        if "HTTP 401" in message:
            return "UNAUTHORIZED"
        if "HTTP 403" in message:
            return "FORBIDDEN"
        if "HTTP 429" in message:
            return "RATE_LIMITED"
        return "API_UNAVAILABLE"
    except (KeyError, ValueError, TypeError):
        return "UNEXPECTED_RESPONSE"


MESSAGES = {
    "CONNECTED": "Token aceito; acesso de leitura ao saldo e à biblioteca confirmado.",
    "NOT_CONFIGURED": "PIXELLAB_API_TOKEN ausente dos Secrets desta execução.",
    "UNAUTHORIZED": "Token rejeitado pelo PixelLab (401).",
    "FORBIDDEN": "Token sem permissão para esta consulta (403).",
    "RATE_LIMITED": "API recusou por limite temporário (429).",
    "API_UNAVAILABLE": "A API não respondeu normalmente; verifique o serviço/rede.",
    "UNEXPECTED_BALANCE_RESPONSE": "Resposta de saldo em formato inesperado.",
    "UNEXPECTED_LIBRARY_RESPONSE": "Resposta da biblioteca em formato inesperado.",
    "UNEXPECTED_RESPONSE": "Resposta inesperada na verificação.",
}


def main() -> None:
    result = verify_connection(os.environ.get("PIXELLAB_API_TOKEN", ""))
    print("PIXELLAB_CONNECTION_STATUS=" + result)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write("## PixelLab — teste de conexão sem custos de geração\n\n")
            output.write("**Resultado:** " + result + "\n\n")
            output.write(MESSAGES[result] + "\n\n")
            output.write("Somente requisições GET de leitura. Nenhuma imagem ou animação foi gerada.\n")
    if result != "CONNECTED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
