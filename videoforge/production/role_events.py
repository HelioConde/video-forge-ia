"""Verified production-role check runs for the public VideoForge office.

This is NOT an AI-agent runtime. It reports work performed by trusted
AutoEditor backend operations to GitHub Checks using the short-lived
GITHUB_TOKEN (checks:write). Never includes prompts, media, OAuth or tokens.

If GitHub telemetry is unavailable the video may still run, but the
dashboard must honestly remain unconnected.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO = "HelioConde/video-forge-ia"
PREFIX = "VideoForge Pipeline / "
ROLES = {
    "diretor": "Validar briefing de producao",
    "roteirista": "Validar roteiro recebido dos agentes",
    "narrador": "Gerar voz Edge TTS com marcacoes",
    "artista": "Gerar imagens reais pelo provedor integrado",
    "animador": "Preparar composicao e camera Remotion",
    "editor": "Renderizar video MP4 com Remotion",
    "revisor": "Verificar MP4 real, formato e integridade",
    "subgerente": "Auditar decisao editorial com evidencias verificaveis",
}
EDITORIAL_ROLES = {
    "diretor": "O gerente do canal seleciona a pauta com metricas e bloqueios",
    "roteirista": "O pesquisador com IA investiga e propoe pautas sem escolhê-las",
    "subgerente": "Audita duplicacoes, pausas e escolha do gerente",
}
_SHA = re.compile(r"^[a-f0-9]{40}$")
_RUN = re.compile(r"^[0-9]{5,22}$")
_SHELL_SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")


class StageEvidenceError(ValueError):
    pass


def valid_context(env: dict | None = None) -> dict | None:
    env = os.environ if env is None else env
    token = env.get("VF_CHECK_TOKEN")
    repo = env.get("GITHUB_REPOSITORY")
    sha = env.get("GITHUB_SHA")
    run = env.get("GITHUB_RUN_ID")
    if not token or repo != REPO or not _SHA.fullmatch(sha or "") or not _RUN.fullmatch(run or ""):
        return None
    return {"token": token, "sha": sha, "run": run}


def _request(context: dict, method: str, endpoint: str, body: dict) -> dict:
    url = "https://api.github.com/repos/" + REPO + endpoint
    if method not in ("POST", "PATCH") or not endpoint.startswith("/check-runs"):
        raise ValueError("TELEMETRY_ENDPOINT_NOT_ALLOWED")
    data = json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    req = Request(url, data=data, method=method, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": "Bearer " + context["token"],
        "Content-Type": "application/json",
        "User-Agent": "VideoForge-Trusted-Backend",
    })
    with urlopen(req, timeout=8) as response:
        if response.status not in (200, 201):
            raise ValueError("TELEMETRY_HTTP_FAILURE")
        return json.loads(response.read(50000).decode("utf-8"))



def _status_request(context: dict, body: dict) -> dict:
    """GitHub commit status: independent public-safe fallback for Checks API.

    Only static role names, channel and workflow IDs are published. The
    response never includes a secret or payload from the provider.
    """
    req = Request(
        "https://api.github.com/repos/" + REPO + "/statuses/" + context["sha"],
        data=json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode("utf-8"),
        method="POST", headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": "Bearer " + context["token"],
            "Content-Type": "application/json",
            "User-Agent": "VideoForge-Trusted-Backend",
        }
    )
    with urlopen(req, timeout=8) as response:
        if response.status != 201:
            raise ValueError("ROLE_COMMIT_STATUS_NOT_CREATED")
        return json.loads(response.read(50000).decode("utf-8"))



class CheckReporter:
    def __init__(self, env: dict | None = None, *, channel: str | None = None,
                 workflow_kind: str = "autoeditor"):
        if workflow_kind not in ("autoeditor", "editorial"):
            raise StageEvidenceError("TELEMETRY_WORKFLOW_KIND_INVALID")
        self.workflow_kind = workflow_kind
        self.context = valid_context(env)
        self.channel = channel if isinstance(channel, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", channel) else None
        self.checks: dict[str, int] = {}
        self.started_roles: set[str] = set()

    def _emit(self, method: str, endpoint: str, data: dict) -> dict | None:
        if not self.context:
            return None
        try:
            return _request(self.context, method, endpoint, data)
        except (HTTPError, URLError, OSError, ValueError, TimeoutError, KeyError, TypeError):
            # Never log exception bodies or headers: secrets could leak.
            print("VIDEOFORGE_ROLE_TELEMETRY_UNAVAILABLE", file=sys.stderr)
            return None

    def _emit_status(self, role: str, state: str) -> None:
        """Write a stage transition only with an authenticated runner context."""
        if not self.context or not self.channel:
            return
        if state not in ("pending", "success", "failure"):
            raise StageEvidenceError("TELEMETRY_STATUS_INVALID")
        url = "https://github.com/" + REPO + "/actions/runs/" + self.context["run"]
        body = {
            "state": state,
            "context": "VideoForge Stage / " + self.workflow_kind + " / " + self.channel + " / " + role,
            "target_url": url,
            "description": (
                "Etapa em execucao no backend; nao equivale a IA autonoma"
                if state == "pending" else
                "Etapa tecnica concluida com evidencia; revisao editorial pendente"
                if state == "success" else
                "Etapa tecnica interrompida; verificar GitHub Actions"
            ),
        }
        try:
            _status_request(self.context, body)
        except (HTTPError, URLError, OSError, ValueError, TimeoutError, KeyError, TypeError):
            print("VIDEOFORGE_ROLE_STATUS_TELEMETRY_UNAVAILABLE", file=sys.stderr)

    def start(self, role: str) -> None:
        valid_roles = EDITORIAL_ROLES if self.workflow_kind == "editorial" else ROLES
        if role not in valid_roles:
            raise StageEvidenceError("TELEMETRY_UNKNOWN_ROLE")
        if not self.context or not self.channel:
            return
        self.started_roles.add(role)
        self._emit_status(role, "pending")
        url = ("https://github.com/" + REPO + "/actions/runs/" + self.context["run"])
        payload = {
            "name": PREFIX + role,
            "head_sha": self.context["sha"],
            "external_id": "vf-" + self.workflow_kind + ":" + self.context["run"] + ":" + self.channel + ":" + role,
            "details_url": url,
            "status": "in_progress",
            "output": {
                "title": "Etapa do pipeline em andamento",
                "summary": valid_roles[role] + (
                    ". Pesquisa editorial com IA supervisionada, nao publicacao."
                    if self.workflow_kind == "editorial" else
                    ". Executor tecnico: AutoEditor. Nao significa agente autonomo de IA."
                ),
            },
        }
        result = self._emit("POST", "/check-runs", payload)
        if result and type(result.get("id")) is int:
            self.checks[role] = result["id"]

    def finish(self, role: str, *, passed: bool) -> None:
        if role in self.started_roles:
            self.started_roles.remove(role)
            self._emit_status(role, "success" if passed else "failure")
        if role not in self.checks:
            return
        endpoint = "/check-runs/" + str(self.checks.pop(role))
        self._emit("PATCH", endpoint, {
            "status": "completed",
            "conclusion": "success" if passed else "failure",
            "output": {
                "title": "Etapa concluida" if passed else "Etapa interrompida",
                "summary": (EDITORIAL_ROLES if self.workflow_kind == "editorial" else ROLES)[role] + (". Entrega confirmada no executor."
                                          if passed else
                                          ". Etapa falhou; revisar GitHub Actions. "
                                          "Nenhum upload autorizado."),
            },
        })


@contextmanager
def role_task(role: str, *, evidence: tuple[Path, ...] = (), reporter: CheckReporter | None = None):
    """Emit start/finish around a real operation. Never fake evidence.

    Disabled locally without an authorized Actions token. A completed
    check is recorded ONLY after all expected files exist and are nonempty.
    """
    reporter = reporter or CheckReporter()
    valid_roles = EDITORIAL_ROLES if reporter.workflow_kind == "editorial" else ROLES
    if role not in valid_roles:
        raise StageEvidenceError("TELEMETRY_UNKNOWN_ROLE")
    reporter.start(role)
    try:
        yield
        for file in evidence:
            file = Path(file)
            if file.is_symlink() or not file.is_file() or file.stat().st_size == 0:
                raise StageEvidenceError("TELEMETRY_OUTPUT_EVIDENCE_MISSING")
    except BaseException:
        reporter.finish(role, passed=False)
        raise
    else:
        reporter.finish(role, passed=True)
