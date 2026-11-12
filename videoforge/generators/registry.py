"""Catálogo declarativo de geradores de vídeo, sem lista fixa de nichos.

Cada pasta em geradores/<id>/gerador.json é um módulo de produção independente.
O catálogo NÃO executa código, não importa plugins externos, não faz chamadas
de IA, não renderiza e não publica. Apenas valida e seleciona contratos.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from videoforge.production.image_policy import load_image_policy

ROOT = Path(__file__).resolve().parents[2]
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FILENAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}$")


class GeneratorConfigError(ValueError):
    """Definição de gerador inválida ou não confiável."""


def _safe_id(value: Any, label: str = "gerador") -> str:
    if not isinstance(value, str) or len(value) > 80 or not _ID.fullmatch(value):
        raise GeneratorConfigError(f"{label.upper()}_ID_INVALID")
    return value


def _text(value: Any, label: str, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise GeneratorConfigError(f"{label.upper()}_INVALID")
    return value.strip()


def validate_definition(value: Any, *, expected_id: str | None = None) -> dict:
    """Valida DAG, origem das imagens e bloqueio de publicação.

    Suporta etapas novas sem alterar o código. 'image_generation' e 'render'
    são identificadores de contrato obrigatórios para qualquer vídeo.
    """
    if not isinstance(value, dict) or value.get("schema") != "videoforge/generator/v1":
        raise GeneratorConfigError("GENERATOR_SCHEMA_INVALID")
    gen_id = _safe_id(value.get("id"))
    if expected_id is not None and gen_id != expected_id:
        raise GeneratorConfigError("GENERATOR_FOLDER_ID_MISMATCH")
    _text(value.get("nome"), "nome", 120)
    _text(value.get("descricao"), "descricao", 800)
    status = value.get("status")
    if status not in ("planned", "ready_for_backend", "active"):
        raise GeneratorConfigError("GENERATOR_STATUS_INVALID")
    if value.get("auto_publish_enabled") is not False or value.get("requires_human_approval") is not True:
        raise GeneratorConfigError("GENERATOR_MUST_NOT_AUTOPUBLISH")
    if value.get("execution_enabled") is not False:
        # The declarative catalog itself does not grant execution.
        raise GeneratorConfigError("GENERATOR_CATALOG_CANNOT_ENABLE_EXECUTION")
    profile = value.get("perfil")
    if not isinstance(profile, dict):
        raise GeneratorConfigError("GENERATOR_PROFILE_INVALID")
    for key in ("publico", "estilo", "direcao"):
        _text(profile.get(key), f"perfil_{key}", 800)
    stages = value.get("pipeline")
    if not isinstance(stages, list) or not 3 <= len(stages) <= 64:
        raise GeneratorConfigError("GENERATOR_PIPELINE_INVALID")
    ids, outputs, deps = set(), set(), {}
    operations = {}
    for stage in stages:
        if not isinstance(stage, dict):
            raise GeneratorConfigError("GENERATOR_STAGE_INVALID")
        sid = _safe_id(stage.get("id"), "stage")
        operation = _safe_id(stage.get("operation"), "operation")
        role = _safe_id(stage.get("agent"), "agent")
        deliverable = stage.get("output")
        if (not isinstance(deliverable, str) or len(deliverable) > 105
                or not _FILENAME.fullmatch(deliverable) or
                deliverable in (".", "..")):
            raise GeneratorConfigError("GENERATOR_STAGE_OUTPUT_UNSAFE")
        previous = stage.get("after")
        if not isinstance(previous, list) or len(previous) > 32 or any(
            not isinstance(x, str) or not _ID.fullmatch(x) for x in previous
        ) or len(set(previous)) != len(previous):
            raise GeneratorConfigError("GENERATOR_STAGE_DEPENDENCIES_INVALID")
        if sid in ids or deliverable in outputs:
            raise GeneratorConfigError("GENERATOR_STAGE_DUPLICATE")
        ids.add(sid)
        outputs.add(deliverable)
        deps[sid] = previous
        operations[sid] = operation
        if operation == "image-generation" and stage.get("source") != "integrated-image-generator":
            raise GeneratorConfigError("GENERATOR_IMAGE_SOURCE_REQUIRED")
        if operation != "image-generation" and stage.get("source") == "integrated-image-generator":
            raise GeneratorConfigError("GENERATOR_IMAGE_SOURCE_MISPLACED")
    if any(not set(after) <= ids for after in deps.values()):
        raise GeneratorConfigError("GENERATOR_STAGE_DEPENDENCY_NOT_FOUND")
    visited, visiting = set(), set()

    def visit(node: str) -> None:
        if node in visiting:
            raise GeneratorConfigError("GENERATOR_PIPELINE_CYCLE")
        if node in visited:
            return
        visiting.add(node)
        for dependency in deps[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in ids:
        visit(node)
    images = [i for i, op in operations.items() if op == "image-generation"]
    renders = [i for i, op in operations.items() if op == "render"]
    reviews = [i for i, op in operations.items() if op == "quality-review"]
    if not images or not renders or not reviews:
        raise GeneratorConfigError("GENERATOR_IMAGES_RENDER_QA_REQUIRED")

    def ancestry(node: str) -> set[str]:
        result = set()
        for ancestor in deps[node]:
            result.add(ancestor)
            result.update(ancestry(ancestor))
        return result

    if any(not set(images) <= ancestry(render) for render in renders):
        raise GeneratorConfigError("GENERATOR_RENDER_REQUIRES_ALL_IMAGES")
    if any(not set(renders) <= ancestry(qa) for qa in reviews):
        raise GeneratorConfigError("GENERATOR_QA_REQUIRES_RENDER")
    return value


def load_generator(generator_id: str, *, root: Path = ROOT) -> dict:
    """Busca definição de um gerador por pasta; falha fechada em IDs suspeitos."""
    generator_id = _safe_id(generator_id)
    base = Path(root).resolve() / "geradores"
    folder = base / generator_id
    path = folder / "gerador.json"
    if folder.is_symlink() or path.is_symlink() or not path.is_file():
        raise GeneratorConfigError("GENERATOR_NOT_REGISTERED")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise GeneratorConfigError("GENERATOR_JSON_INVALID") from None
    return validate_definition(value, expected_id=generator_id)


def list_generators(*, root: Path = ROOT) -> list[dict]:
    """Descoberta automática: qualquer novo módulo válido aparece no catálogo."""
    base = Path(root).resolve() / "geradores"
    if not base.is_dir() or base.is_symlink():
        return []
    result = []
    for folder in sorted(base.iterdir(), key=lambda p: p.name):
        if folder.is_dir() and not folder.is_symlink() and _ID.fullmatch(folder.name):
            if (folder / "gerador.json").is_file():
                value = load_generator(folder.name, root=root)
                result.append({
                    "id": value["id"], "nome": value["nome"],
                    "status": value["status"],
                    "etapas": len(value["pipeline"]),
                    "execution_enabled": False,
                })
    return result


def resolve_generator(channel: dict, video: dict, *, root: Path = ROOT) -> dict | None:
    """Vídeo > padrão do canal. Sem escolha, mantém compatibilidade legada."""
    selected = video["gerador"] if "gerador" in video else channel.get("gerador_padrao")
    if selected is None:
        return None
    return load_generator(_safe_id(selected), root=root)


def build_generator_plan(definition: dict, *, root: Path = ROOT) -> dict:
    """Devolve DAG declarativa para futuros executores independentes.

    Sempre aplica a política global de imagens; um módulo especializado
    não pode habilitar fallback visual, execução ou publicação.
    """
    definition = validate_definition(definition)
    policy = load_image_policy(Path(root))
    if policy["mode"] != "generator_only" or policy["on_failure"] != "abort_video":
        raise GeneratorConfigError("GLOBAL_GENERATOR_IMAGE_POLICY_VIOLATED")
    return {
        "schema": "videoforge/generator-plan/v1",
        "generator_id": definition["id"],
        "mode": "plan_only",
        "execution_enabled": False,
        "auto_publish_enabled": False,
        "requires_human_approval": True,
        "image_source": "integrated_image_generator_only",
        "image_failure": "abort_video",
        "tasks": [{
            "id": s["id"], "operation": s["operation"],
            "responsavel": s["agent"], "depende_de": list(s["after"]),
            "entrega_esperada": s["output"],
            "execution_status": "not_started",
        } for s in definition["pipeline"]],
    }
