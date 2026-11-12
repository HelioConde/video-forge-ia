"""Visual-bible contract for the VideoForge AutoEditor image artist and reviewer.

All later frames must edit the SAME approved anchor image, not make unrelated
text-to-image generations. This enforces traceable reference usage, not a claim
that computer vision or a human approved the actual artistic similarity.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

STYLE = "cinematic hand-painted 2D anime illustration"
_REQUIRED = ("character_id", "identity", "hair", "eyes", "wardrobe", "accessories", "render_style")
_BANNED = re.compile(
    r"(?i)\b(photorealistic|photo-realistic|photographic|live.action|hyperrealistic|"
    r"foto(realista|grafia|gr[aá]fica)?|fotorealista|realismo.fotogr[aá]fico|"
    r"3d.render|cgi.render)\b"
)


class VisualLockError(ValueError):
    """Public-safe validation error."""


def validate_visual_lock(raw: object) -> dict:
    if not isinstance(raw, dict) or raw.get("schema") != "videoforge/visual-bible/v1":
        raise VisualLockError("AUTOEDITOR_VISUAL_BIBLE_REQUIRED")
    if raw.get("mode") != "anchor_image_edit" or raw.get("anchor_scene") != 1:
        raise VisualLockError("AUTOEDITOR_ANCHOR_EDIT_MODE_REQUIRED")
    if raw.get("render_style") != STYLE:
        raise VisualLockError("AUTOEDITOR_STYLE_MUST_BE_LOCKED")
    if raw.get("require_human_visual_review") is not True:
        raise VisualLockError("AUTOEDITOR_VISUAL_REVIEW_REQUIRED")
    for field in _REQUIRED:
        value = raw.get(field)
        if not isinstance(value, str) or not 3 <= len(value.strip()) <= 500:
            raise VisualLockError("AUTOEDITOR_VISUAL_BIBLE_FIELD_INVALID")
        if _BANNED.search(value):
            raise VisualLockError("AUTOEDITOR_VISUAL_STYLE_CONFLICT")
    if not re.fullmatch("[a-z0-9-]{3,60}", raw["character_id"]):
        raise VisualLockError("AUTOEDITOR_VISUAL_CHARACTER_ID_INVALID")
    return {key: raw[key].strip() for key in _REQUIRED} | {
        "schema": "videoforge/visual-bible/v1",
        "mode": "anchor_image_edit",
        "anchor_scene": 1,
        "require_human_visual_review": True,
    }


def visual_bible_digest(lock: dict) -> str:
    return sha256(json.dumps(lock, ensure_ascii=False, sort_keys=True)
                  .encode("utf-8")).hexdigest()


def scene_prompt(scene: dict, bible: dict, *, first: bool) -> str:
    if _BANNED.search(scene["prompt_imagem"]):
        raise VisualLockError("AUTOEDITOR_SCENE_CONTRADICTS_VISUAL_BIBLE")
    core = (
        f"ART DIRECTION LOCK. Produce only a {bible['render_style']}. "
        "Flat hand-drawn anime anatomy and coherent painted shading; "
        "NEVER photography, CGI, 3D, alternate anime genres or realistic human portraits. "
        f"CHARACTER ID {bible['character_id']}: {bible['identity']}. "
        f"Hair: {bible['hair']}. Eyes: {bible['eyes']}. "
        f"Clothing: {bible['wardrobe']}. Accessories: {bible['accessories']}. "
        "Keep the same face geometry, age appearance, hairstyle, outfit colors, "
        "accessory shapes, clocktower architecture and painterly brush style "
        "throughout the entire video. "
        "Only vary pose, camera, lighting, expression, scene action and location. "
        "Single 9:16 composition, no lettering, subtitles, split panels or UI. "
    )
    if not first:
        core += (
            "EDIT THE UPLOADED SCENE ONE REFERENCE IMAGE. The uploaded image is the "
            "CANONICAL art/face/outfit/style source. Preserve that character's "
            "specific facial identity and visual medium. Replace the background "
            "and rearrange the pose as required, not the character design. "
            "Do not reinterpret the reference as a photograph. "
        )
    else:
        core += (
            "This is scene ONE: establish the definitive face, style and outfit "
            "that all subsequent edits must use as a reference. "
        )
    return core + "SCENE STORYBOARD: " + scene["prompt_imagem"]


def verify_anchor_trace(assets: list, bible: dict) -> dict:
    """Prove how images were requested, never pretend to judge visual similarity."""
    if not isinstance(assets, list) or not assets:
        raise VisualLockError("AUTOEDITOR_VISUAL_TRACE_MISSING")
    expected_digest = visual_bible_digest(bible)
    anchor = assets[0]
    if (anchor.get("scene") != 1
            or anchor.get("generation_mode") != "canonical_anchor"
            or anchor.get("visual_bible_sha256") != expected_digest
            or not isinstance(anchor.get("output_sha256"), str)):
        raise VisualLockError("AUTOEDITOR_CANONICAL_ANCHOR_INVALID")
    for i, a in enumerate(assets[1:], start=2):
        if (a.get("scene") != i
                or a.get("generation_mode") != "reference_image_edit"
                or a.get("anchor_scene") != 1
                or a.get("anchor_sha256") != anchor["output_sha256"]
                or a.get("visual_bible_sha256") != expected_digest):
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
