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


class CheckReporter:
    def __init__(self, env: dict | None = None, *, channel: str | None = None):
        self.context = valid_context(env)
        self.channel = channel if isinstance(channel, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", channel) else None
        self.checks: dict[str, int] = {}

    def _emit(self, method: str, endpoint: str, data: dict) -> dict | None:
        if not self.context:
            return None
        try:
            return _request(self.context, method, endpoint, data)
        except (HTTPError, URLError, OSError, ValueError, TimeoutError, KeyError, TypeError):
            # Never log exception bodies or headers: secrets could leak.
            print("VIDEOFORGE_ROLE_TELEMETRY_UNAVAILABLE", file=sys.stderr)
            return None

    def start(self, role: str) -> None:
        if role not in ROLES:
            raise StageEvidenceError("TELEMETRY_UNKNOWN_ROLE")
        if not self.context or not self.channel:
            return
        url = ("https://github.com/" + REPO + "/actions/runs/" + self.context["run"])
        payload = {
            "name": PREFIX + role,
            "head_sha": self.context["sha"],
            "external_id": "vf-autoeditor:" + self.context["run"] + ":" + self.channel + ":" + role,
            "details_url": url,
            "status": "in_progress",
            "output": {
                "title": "Etapa do pipeline em andamento",
                "summary": ROLES[role] + ". Executor tecnico: AutoEditor. "
                           "Nao significa agente autonomo de IA.",
            },
        }
        result = self._emit("POST", "/check-runs", payload)
        if result and type(result.get("id")) is int:
            self.checks[role] = result["id"]

    def finish(self, role: str, *, passed: bool) -> None:
        if role not in self.checks:
            return
        endpoint = "/check-runs/" + str(self.checks.pop(role))
        self._emit("PATCH", endpoint, {
            "status": "completed",
            "conclusion": "success" if passed else "failure",
            "output": {
                "title": "Etapa concluida" if passed else "Etapa interrompida",
                "summary": ROLES[role] + (". Entrega confirmada no executor."
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
    if role not in ROLES:
        raise StageEvidenceError("TELEMETRY_UNKNOWN_ROLE")
    reporter = reporter or CheckReporter()
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
