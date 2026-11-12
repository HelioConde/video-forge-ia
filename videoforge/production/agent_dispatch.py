"""Safe bridge from the 18-stage dispatcher to Codex Proxy text agents.

Planning is offline. Execution is opt-in on a trusted private backend, never
by the public Pages UI or automatically by the planning workflow.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Mapping

from videoforge.proxy.agent_gateway import (
    invoke_agent, registered_agents,
)
from videoforge.proxy.client import ProxyClient
from videoforge.proxy.roles import STAGE_ENDPOINT

from .dispatcher import ROOT, STAGES, ready_tasks


class DispatchError(ValueError):
    """Non-sensitive dispatch failure."""


TEXT_CAPABILITIES = frozenset({"chat", "responses"})
STAGE_INSTRUCTIONS = {
    "briefing": "Redigir briefing editorial de producao para revisao",
    "pesquisa": "Preparar pesquisa fundamentada para revisao editorial",
    "roteiro": "Redigir roteiro do video para revisao editorial",
    "titulo": "Preparar alternativas de titulo para revisao",
    "descricao": "Redigir descricao do video para revisao",
    "tags": "Propor tags e palavras-chave sem inventar metricas",
    "storyboard": "Propor sequencia textual de cenas para revisao",
    "qa_conteudo": "Escrever avaliacao preliminar sem aprovar o QA",
}


def _trusted_task(plan: dict, task_id: str, *, root: Path = ROOT) -> dict:
    if not isinstance(plan, dict) or plan.get("schema") != "videoforge/production-delegation/v1":
        raise DispatchError("DISPATCH_PLAN_INVALID")
    demand = plan.get("demand")
    if not isinstance(demand, dict):
        raise DispatchError("DISPATCH_DEMAND_INVALID")
    if not isinstance(demand.get("id"), str) or not (
        demand["id"].replace("-", "").replace("_", "").isalnum()
        and len(demand["id"]) <= 64
    ):
        raise DispatchError("DISPATCH_ID_INVALID")
    if (not isinstance(demand.get("canal"), str)
            or not demand["canal"].replace("-", "").isalnum()
            or not (root / "canal" / demand["canal"] / "canal.json").is_file()):
        raise DispatchError("DISPATCH_CHANNEL_INVALID")
    if plan.get("publishing_enabled") is not False:
        raise DispatchError("DISPATCH_PUBLISHING_MUST_BE_DISABLED")
    if not isinstance(task_id, str):
        raise DispatchError("DISPATCH_TASK_INVALID")
    expected = {stage_id: (worker, list(deps), filename)
                for stage_id, worker, deps, filename in STAGES}
    if task_id not in expected:
        raise DispatchError("DISPATCH_TASK_UNKNOWN")
    if STAGE_ENDPOINT.get(task_id) not in TEXT_CAPABILITIES:
        raise DispatchError("DISPATCH_NOT_TEXT_STAGE")
    tasks = plan.get("tasks")
    if not isinstance(tasks, list):
        raise DispatchError("DISPATCH_TASKS_INVALID")
    matching = [t for t in tasks if isinstance(t, dict) and t.get("id") == task_id]
    if len(matching) != 1:
        raise DispatchError("DISPATCH_TASK_AMBIGUOUS")
    task = matching[0]
    worker, dependencies, filename = expected[task_id]
    if (task.get("responsavel") != worker or
            task.get("depende_de") != dependencies or
            task.get("entrega_esperada") != filename):
        raise DispatchError("DISPATCH_ROLE_OR_DEPENDENCY_MISMATCH")
    if worker not in registered_agents(root=root):
        raise DispatchError("DISPATCH_WORKER_NOT_REGISTERED")
    if task_id not in ready_tasks(plan):
        raise DispatchError("DISPATCH_TASK_NOT_READY")
    return {
        "task_id": task_id,
        "role_id": worker,
        "channel": demand["canal"],
        "demand_id": demand["id"],
        "expected_delivery": filename,
        "capability": STAGE_ENDPOINT[task_id],
        "instruction": STAGE_INSTRUCTIONS[task_id],
    }


def plan_text_dispatch(plan: dict, *, root: Path = ROOT) -> dict:
    """List currently ready Proxy text workers without network or credentials."""
    selected = []
    for task in plan.get("tasks", []):
        task_id = task.get("id") if isinstance(task, dict) else None
        if task_id in STAGE_INSTRUCTIONS and task_id in ready_tasks(plan):
            selected.append(_trusted_task(plan, task_id, root=root))
    return {
        "schema": "videoforge/text-agent-dispatch/v1",
        "mode": "planning_only",
        "proxy_requests_sent": 0,
        "publishing_enabled": False,
        "ready_text_agents": selected,
    }


def _private_workspace(path: Path) -> Path:
    if path.is_symlink():
        raise DispatchError("DISPATCH_PRIVATE_DIR_SYMLINK")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise DispatchError("DISPATCH_PRIVATE_DIR_INVALID")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise DispatchError("DISPATCH_PRIVATE_DIR_PERMISSIONS")
    return path


def _exclusive_json(path: Path, value: dict) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        raise DispatchError("DISPATCH_ATTEMPT_ALREADY_RESERVED") from None
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def run_text_draft(
    plan: dict, task_id: str, *, context: str, private_dir: Path,
    authorized: bool = False, model: str | None = None,
    client: ProxyClient | None = None, env: Mapping[str, str] | None = None,
    root: Path = ROOT,
) -> dict:
    """Run at most one approved Proxy call and store a private review draft.

    An exclusive reservation survives failure, so a workflow cannot retry an
    uncertain provider call by accident. It NEVER marks a stage completed.
    An independent trusted backend must review and approve the draft.
    """
    env = os.environ if env is None else env
    if authorized is not True or env.get("VIDEOFORGE_AGENT_EXECUTION_APPROVED") != "yes":
        raise DispatchError("DISPATCH_NOT_AUTHORIZED")
    assignment = _trusted_task(plan, task_id, root=root)
    if not isinstance(context, str) or not 1 <= len(context.strip()) <= 16000:
        raise DispatchError("DISPATCH_CONTEXT_INVALID")
    if not isinstance(private_dir, Path):
        raise DispatchError("DISPATCH_PRIVATE_DIR_INVALID")

    workspace = _private_workspace(private_dir)
    ticket = workspace / (assignment["demand_id"] + "-" + task_id + ".ticket.json")
    draft = workspace / (assignment["demand_id"] + "-" + task_id + ".draft.json")
    _exclusive_json(ticket, {
        "schema": "videoforge/agent-task-reservation/v1",
        "demand_id": assignment["demand_id"],
        "channel": assignment["channel"],
        "task_id": task_id,
        "role_id": assignment["role_id"],
        "state": "reserved_no_automatic_retry",
    })
    # Do not delete this ticket on failure. The runner must reconcile
    # charges/outcomes manually before any attempt at re-execution.
    result = invoke_agent(
        role_id=assignment["role_id"],
        task=assignment["instruction"],
        context=context,
        model=model,
        authorized=True,
        env=env,
        client=client,
        root=root,
    )
    if result.get("role_id") != assignment["role_id"]:
        raise DispatchError("DISPATCH_RESULT_ROLE_MISMATCH")
    private_artifact = {
        "schema": "videoforge/agent-task-draft/v1",
        "demand_id": assignment["demand_id"],
        "channel": assignment["channel"],
        "task_id": task_id,
        "role_id": assignment["role_id"],
        "provider": "codex_proxy",
        "model": result["model"],
        "content": result["content"],
        "content_sha256": hashlib.sha256(result["content"].encode("utf-8")).hexdigest(),
        "status": "awaiting_independent_review",
        "artifact_verified": False,
        "video_uploaded": False,
        "proxy_requests_sent": 1,
    }
    _exclusive_json(draft, private_artifact)
    return {
        "schema": "videoforge/agent-task-receipt/v1",
        "demand_id": assignment["demand_id"],
        "task_id": task_id,
        "role_id": assignment["role_id"],
        "status": "awaiting_independent_review",
        "artifact_verified": False,
        "publishing_enabled": False,
        "proxy_requests_sent": 1,
    }
