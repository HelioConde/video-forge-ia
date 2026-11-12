"""Relaciona tarefas reais do diretor a capacidades do proxy sem executa-las."""
from __future__ import annotations

# O proxy gera texto e imagem; nao substitui TTS, render, animacao ou YouTube.
STAGE_ENDPOINT = {
    "briefing": "responses",
    "pesquisa": "responses",
    "roteiro": "responses",
    "titulo": "chat",
    "descricao": "chat",
    "tags": "chat",
    "storyboard": "responses",
    "thumbnail": "images_generate",
    "visuais": "images_generate",
    "qa_conteudo": "responses",
}
HUMAN_STAGES = frozenset({"aprovacao"})
OTHER_BACKENDS = frozenset({"animacao", "narracao", "legendas", "audio",
                            "edicao", "qa_tecnico", "publicacao"})


def plan_bindings(plan: dict, *, reference_images: bool = False) -> dict:
    """Anexa planos de capacidade por tarefa, sem criar trabalho ou cobrar API."""
    if plan.get("schema") != "videoforge/production-delegation/v1":
        raise ValueError("Plano de producao incompatível")
    bindings = []
    for stage in plan["tasks"]:
        task_id = stage["id"]
        endpoint = STAGE_ENDPOINT.get(task_id)
        if task_id in ("thumbnail", "visuais") and reference_images:
            endpoint = "images_edit"
        owner = "codex_proxy" if endpoint else (
            "human" if task_id in HUMAN_STAGES else "other_backend")
        if not endpoint and task_id not in HUMAN_STAGES | OTHER_BACKENDS:
            raise ValueError("Tarefa sem provedor: " + task_id)
        bindings.append({
            "task_id": task_id, "responsavel": stage["responsavel"],
            "backend": owner, "capability": endpoint,
            "requires_approval": task_id in {"thumbnail", "visuais", "publicacao"},
            "execution_status": "not_started",
            "image_source_required": ("generator_only" if task_id in
                                      {"thumbnail", "visuais"} else None),
            "assistant_image_generation_permitted": False,
            "visual_fallback_permitted": False,
        })
    return {
        "schema": "videoforge/proxy-stage-bindings/v1",
        "producer": "AutoEditorVideo-compatible-Codex-Proxy",
        "mode": "plan_only", "active_connection": False,
        "calls_sent": 0, "models_executed": 0,
        "bindings": bindings,
    }
