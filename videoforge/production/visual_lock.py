"""Visual continuity contract for all VideoForge AutoEditor art agents.

The image model performs every image operation through Codex Proxy.
If an approved image reference exists, edit it for scene 1; otherwise create
ONE canonical scene 1 and pass its bytes as the reference for every later edit.
Reference use is auditable; matching appearance still requires independent QA.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

_REQUIRED = ("character_id", "identity", "hair", "eyes", "wardrobe",
             "accessories", "render_style")
_STYLES = frozenset({"illustration", "photographic", "3d"})
_MISMATCH = {
    "illustration": re.compile(r"(?i)\b(photo(?:realistic|graphic)?|hyperrealistic|"
                               r"realismo fotogr[aá]fico|foto(?:rrealista|realista)|"
                               r"3d[ -]render|cgi[ -]render|live[ -]action)\b"),
    "photographic": re.compile(r"(?i)\b(anime|cartoon|cel[ -]shaded|"
                               r"flat illustration|pencil sketch|2d animation)\b"),
    "3d": re.compile(r"(?i)\b(photograph|2d anime|flat illustration|"
                     r"hand[ -]drawn[ -]cartoon)\b"),
}
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


class VisualLockError(ValueError):
    """Public-safe validation error, with no prompt contents in messages."""


def validate_visual_lock(raw: object) -> dict:
    if not isinstance(raw, dict) or raw.get("schema") != "videoforge/visual-bible/v1":
        raise VisualLockError("AUTOEDITOR_VISUAL_BIBLE_REQUIRED")
    if raw.get("mode") != "anchor_image_edit" or raw.get("anchor_scene") != 1:
        raise VisualLockError("AUTOEDITOR_ANCHOR_EDIT_MODE_REQUIRED")
    if raw.get("style_family") not in _STYLES:
        raise VisualLockError("AUTOEDITOR_STYLE_FAMILY_INVALID")
    if raw.get("require_human_visual_review") is not True:
        raise VisualLockError("AUTOEDITOR_VISUAL_REVIEW_REQUIRED")
    for field in _REQUIRED:
        value = raw.get(field)
        if not isinstance(value, str) or not 3 <= len(value.strip()) <= 500:
            raise VisualLockError("AUTOEDITOR_VISUAL_BIBLE_FIELD_INVALID")
        if _MISMATCH[raw["style_family"]].search(value):
            raise VisualLockError("AUTOEDITOR_VISUAL_STYLE_CONFLICT")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", raw["character_id"]):
        raise VisualLockError("AUTOEDITOR_VISUAL_CHARACTER_ID_INVALID")
    reference_path = raw.get("reference_path")
    if reference_path is not None:
        if (not isinstance(reference_path, str)
                or not 5 <= len(reference_path) <= 240
                or Path(reference_path).is_absolute()
                or ".." in Path(reference_path).parts
                or "\\" in reference_path
                or Path(reference_path).suffix.lower() not in _IMAGE_EXT):
            raise VisualLockError("AUTOEDITOR_VISUAL_REFERENCE_PATH_INVALID")
    return {key: raw[key].strip() for key in _REQUIRED} | {
        "schema": "videoforge/visual-bible/v1",
        "mode": "anchor_image_edit",
        "anchor_scene": 1,
        "style_family": raw["style_family"],
        "reference_path": reference_path,
        "require_human_visual_review": True,
    }


def resolve_reference_image(bible: dict, *, channel: str, root: Path) -> Path | None:
    """Allow references only from a channel's own reviewed asset directory."""
    relative = bible["reference_path"]
    if relative is None:
        return None
    expected_prefix = ("canal", channel, "referencias")
    parts = Path(relative).parts
    if len(parts) != 4 or tuple(parts[:3]) != expected_prefix:
        raise VisualLockError("AUTOEDITOR_VISUAL_REFERENCE_OUTSIDE_CHANNEL")
    path = Path(root) / relative
    if path.is_symlink() or not path.is_file() or not 1000 <= path.stat().st_size <= 18_000_000:
        raise VisualLockError("AUTOEDITOR_VISUAL_REFERENCE_INVALID")
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if (image.format not in ("PNG", "JPEG", "WEBP")
                    or image.width < 512 or image.height < 512
                    or image.width * image.height > 18_000_000):
                raise ValueError()
    except (OSError, ValueError, ImportError):
        raise VisualLockError("AUTOEDITOR_VISUAL_REFERENCE_INVALID") from None
    return path


def visual_bible_digest(lock: dict) -> str:
    return sha256(json.dumps(lock, ensure_ascii=False, sort_keys=True)
                  .encode("utf-8")).hexdigest()


def scene_prompt(scene: dict, bible: dict, *, first: bool) -> str:
    base = scene["prompt_imagem"]
    if _MISMATCH[bible["style_family"]].search(base):
        raise VisualLockError("AUTOEDITOR_SCENE_CONTRADICTS_VISUAL_BIBLE")
    style = bible["render_style"]
    core = (
        f"MANDATORY ART-DIRECTION AND VISUAL IDENTITY LOCK. Exactly the same {style} "
        "across the entire story; do not switch rendering medium, linework, "
        "shading language, artistic era or visual treatment. "
        f"CHARACTER {bible['character_id']}: {bible['identity']}. "
        f"Hair: {bible['hair']}. Eyes: {bible['eyes']}. "
        f"Costume: {bible['wardrobe']}. Accessories: {bible['accessories']}. "
        "Preserve facial geometry, apparent age, identity, hairstyle, outfit, "
        "materials, accessory details, architecture and established palette. "
        "Vary only scene events, camera, pose, expression, environment "
        "and physically appropriate lighting. "
        "Vertical 9:16, one coherent scene, no text, UI, watermarks or panels. "
    )
    if first:
        core += (
            "ESTABLISH THE CANONICAL LOOK. This becomes the visual identity "
            "for every following scene. "
        )
    else:
        core += (
            "EDIT THE ATTACHED CANONICAL REFERENCE IMAGE. Its character design, "
            "facial features, outfit and rendering style are binding. "
            "This is a new shot in the same story, NOT a redesign. "
        )
    return core + "CURRENT SCENE: " + base


def verify_anchor_trace(assets: list, bible: dict) -> dict:
    """Verify the actual request chain, NOT artistic similarity."""
    if not isinstance(assets, list) or not assets:
        raise VisualLockError("AUTOEDITOR_VISUAL_TRACE_MISSING")
    expected_digest = visual_bible_digest(bible)
    anchor = assets[0]
    anchor_mode = ("reference_image_edit" if bible["reference_path"] is not None
                   else "canonical_anchor")
    if (anchor.get("scene") != 1
            or anchor.get("generation_mode") != anchor_mode
            or anchor.get("visual_bible_sha256") != expected_digest
            or not isinstance(anchor.get("output_sha256"), str)):
        raise VisualLockError("AUTOEDITOR_CANONICAL_ANCHOR_INVALID")
    for i, item in enumerate(assets[1:], start=2):
        if (item.get("scene") != i
                or item.get("generation_mode") != "reference_image_edit"
                or item.get("anchor_scene") != 1
                or item.get("anchor_sha256") != anchor["output_sha256"]
                or item.get("visual_bible_sha256") != expected_digest):
            raise VisualLockError("AUTOEDITOR_SCENE_NOT_ANCHORED")
    return {
        "schema": "videoforge/visual-continuity-audit/v1",
        "anchor_reference_provenance_verified": True,
        "anchor_scene": 1,
        "reference_image_edits_verified": max(0, len(assets) - 1),
        "visual_bible_sha256": expected_digest,
        "actual_visual_identity_verified": False,
        "human_visual_review": False,
        "status": "technical_reference_chain_verified_visual_review_pending",
        "render_allowed_for_private_preview_only": True,
        "youtube_upload_approved": False,
    }
