"""Read-only GitHub Actions health monitor for VideoForge.

Safe for scheduled runs: public workflow metadata and local roster only.
No Codex Proxy, OAuth, YouTube Analytics, model inference, mutations or uploads.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, parse, request

REPOSITORY = "HelioConde/video-forge-ia"
WORKFLOWS = (
    ("validate.yml", True),
    ("pages.yml", True),
    ("channel-manager-analysis.yml", False),
    ("codex-proxy-backend.yml", False),
    ("external-research-validation.yml", False),
)
MAX_PENDING_MINUTES = 90
SAFE_CONCLUSIONS = frozenset({
    "success", "failure", "cancelled", "skipped", "timed_out",
    "action_required", "neutral", "stale", "startup_failure",
})
DANGEROUS = frozenset({"failure", "timed_out", "action_required", "startup_failure"})


class HealthCheckError(ValueError):
    pass


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except ValueError:
        return None


def assess_runs(name: str, rows: object, *, now: datetime,
                required: bool = False) -> dict:
    """Evaluate only main-branch push CI; never equate it with private AI jobs."""
    if not isinstance(rows, list):
        raise HealthCheckError("GITHUB_RUNS_FORMAT_INVALID")
    valid = [
        x for x in rows if isinstance(x, dict)
        and x.get("head_branch") == "main" and x.get("event") == "push"
        and x.get("status") in ("completed", "queued", "in_progress", "waiting", "pending")
        and parse_time(x.get("created_at")) is not None
        and isinstance(x.get("id"), int) and x["id"] > 0
    ]
    valid.sort(key=lambda x: (x["created_at"], x["id"]), reverse=True)
    if not valid:
        return {"workflow": name, "state": "missing" if required else "not_observed",
                "run_id": None, "problem": required}

    latest = valid[0]
    started = parse_time(latest["created_at"])
    assert started is not None
    age_seconds = max(0, (now - started).total_seconds())
    if latest["status"] != "completed":
        state = "stalled" if age_seconds > MAX_PENDING_MINUTES * 60 else "running"
    else:
        conclusion = latest.get("conclusion")
        state = conclusion if conclusion in SAFE_CONCLUSIONS else "indeterminate"
    return {
        "workflow": name, "state": state, "run_id": latest["id"],
        "problem": state in DANGEROUS or state == "stalled",
    }


def fetch_runs(name: str, *, token: str) -> list[dict]:
    if name not in {item[0] for item in WORKFLOWS}:
        raise HealthCheckError("WORKFLOW_NOT_ALLOWED")
    if not isinstance(token, str) or not token:
        raise HealthCheckError("GITHUB_ACTIONS_READ_TOKEN_MISSING")
    path = parse.quote(name, safe="")
    url = (
        f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/"
        f"{path}/runs?branch=main&event=push&per_page=5"
    )
    req = request.Request(url, method="GET", headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "VideoForge-ReadOnly-Health",
    })
    try:
        with request.urlopen(req, timeout=15) as response:
            raw = response.read(260_001)
    except error.HTTPError as exc:
        raise HealthCheckError("GITHUB_ACTIONS_HTTP_" + str(int(exc.code))) from None
    except (error.URLError, OSError, TimeoutError):
        raise HealthCheckError("GITHUB_ACTIONS_NETWORK_UNAVAILABLE") from None
    if len(raw) > 260_000:
        raise HealthCheckError("GITHUB_ACTIONS_RESPONSE_TOO_LARGE")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise HealthCheckError("GITHUB_ACTIONS_RESPONSE_INVALID") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise HealthCheckError("GITHUB_ACTIONS_RUNS_INVALID")
    return payload["workflow_runs"]


def inspect_local_roster() -> dict:
    """Offline counts from the exact configuration the Pages builder reads."""
    from scripts.build_dashboard_data import make_snapshot
    snapshot = make_snapshot()
    agents = snapshot.get("agentes")
    channels = snapshot.get("canais")
    if not isinstance(agents, list) or not isinstance(channels, list):
        raise HealthCheckError("OFFICE_SNAPSHOT_INVALID")
    if len(agents) != 9 or len(channels) != 5:
        raise HealthCheckError("OFFICE_ROSTER_MISMATCH")
    ids = {x.get("id") for x in agents if isinstance(x, dict)}
    if len(ids) != 9 or "subgerente" not in ids:
        raise HealthCheckError("OFFICE_AGENTS_DUPLICATED_OR_MISSING")
    if any(not isinstance(x, dict) or x.get("status") not in
           {"nao_conectado", "aguardando", "trabalhando", "revisao", "concluido", "erro"}
           for x in agents):
        raise HealthCheckError("OFFICE_AGENT_STATE_INVALID")
    return {"agents_registered": 9, "channels_registered": 5,
            "autonomous_execution_verified": False,
            "public_youtube_analytics_accessed": False}


def make_report(*, token: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    rows = []
    for name, required in WORKFLOWS:
        runs = fetch_runs(name, token=token)
        rows.append(assess_runs(name, runs, now=now, required=required))
    return {
        "schema": "videoforge/read-only-ci-health/v1",
        "source": "main_push_workflow_metadata_and_local_snapshot",
        "workflows": rows,
        "roster": inspect_local_roster(),
        "failures": sum(bool(x["problem"]) for x in rows),
        "proxy_calls": 0,
        "image_calls": 0,
        "youtube_requests": 0,
        "videos_published": 0,
        "code_modified": False,
    }


def write_summary(report: dict, path: Path) -> None:
    lines = [
        "## VideoForge — auditoria automática somente leitura",
        "",
        "Conferência dos últimos runs de **push na main**, sem acessar jobs privados.",
        "",
        "| Workflow | Estado | Execução |",
        "|---|---|---|",
    ]
    for row in report["workflows"]:
        link = (f"[#{row['run_id']}](https://github.com/{REPOSITORY}/actions/runs/"
                f"{row['run_id']})" if row["run_id"] else "—")
        lines.append(f"| \`{row['workflow']}\` | {row['state']} | {link} |")
    lines.extend([
        "",
        "Agentes cadastrados: **9**; gerentes/canais: **5**.",
        "Nenhuma atividade autônoma de IA é inferida destes dados.",
        "Sem Codex Proxy, YouTube API, imagens, geração, upload ou alteração do repositório.",
        "",
        f"Falhas/execuções travadas identificadas: **{report['failures']}**.",
        "Esta execução não corrige automaticamente falhas; a automação de diagnóstico",
        "horária pode investigar e aplicar alterações autorizadas no GitHub.",
    ])
    if path.is_symlink():
        raise HealthCheckError("GITHUB_SUMMARY_PATH_UNSAFE")
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")


def main() -> int:
    if (os.getenv("GITHUB_REPOSITORY") != REPOSITORY
            or os.getenv("GITHUB_EVENT_NAME") not in
            {"schedule", "workflow_dispatch", "push"}):
        print("VIDEOFORGE_AUDIT_RUN_CONTEXT_INVALID")
        return 2
    try:
        report = make_report(token=os.getenv("GH_TOKEN", ""))
        destination = os.getenv("GITHUB_STEP_SUMMARY")
        if destination:
            write_summary(report, Path(destination))
        print("VIDEOFORGE_HEALTH_READONLY_" +
              ("ALERT_" if report["failures"] else "OK_") +
              str(report["failures"]) + "_PROBLEMS")
        return 1 if report["failures"] else 0
    except HealthCheckError as exc:
        # Codes are fixed strings, never print API payloads or credentials.
        print(str(exc))
        return 2
    except (OSError, ValueError, TypeError):
        print("VIDEOFORGE_HEALTH_LOCAL_ERROR")
        return 2


if __name__ == "__main__":
    sys.exit(main())
