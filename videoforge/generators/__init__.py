"""Extensible video generator catalog. Manifests plan only; no paid calls."""
from .registry import (
    GeneratorConfigError, build_generator_plan, list_generators,
    load_generator, resolve_generator, validate_definition,
)

__all__ = [
    "GeneratorConfigError", "build_generator_plan", "list_generators",
    "load_generator", "resolve_generator", "validate_definition",
]
