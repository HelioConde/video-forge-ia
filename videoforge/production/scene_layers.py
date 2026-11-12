"""VideoForge scene-master decomposition into aligned real RGBA art layers.

Only the VideoForge artist calls Codex Proxy: every layer edit references the
actual PNG master of THAT scene. No masking, replacement artwork or inpainting
is silently fabricated by Python. This module verifies provenance, geometry,
alpha, budgets, role assignments and hashes, not visual fidelity: an
independent visual review is always required before publication.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import io
import json
from pathlib import Path
import re


from videoforge.proxy.client import ProxyError

SCHEMA = "videoforge/scene-decomposition/v1"
MODE = "layered_from_master_scene"
CANVAS = (720, 1280)
IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
MAX_PROPS_PER_SCENE = 3
MAX_CHARACTERS_PER_SCENE = 3
MAX_PARTS_PER_SCENE = 4
MAX_IMAGE_REQUESTS = 48


class SceneLayerError(ValueError):
    """Safe error that never contains private prompts or provider response."""


def _identifier(value: object) -> str:
    if not isinstance(value, str) or not 2 <= len(value) <= 64 or not IDENTIFIER.fullmatch(value):
        raise SceneLayerError("LAYERS_INVALID_ID")
    return value


def validate_scene_decomposition(raw: object) -> dict:
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise SceneLayerError("LAYERS_DECOMPOSITION_REQUIRED")
    if raw.get("mode") != MODE or raw.get("require_transparent_rgba") is not True:
        raise SceneLayerError("LAYERS_MASTER_AND_RGBA_REQUIRED")
    if raw.get("require_independent_visual_review") is not True:
        raise SceneLayerError("LAYERS_INDEPENDENT_REVIEW_REQUIRED")
    if set(raw) - {"schema", "mode", "require_transparent_rgba",
                    "require_independent_visual_review"}:
        raise SceneLayerError("LAYERS_UNKNOWN_DECOMPOSITION_SETTINGS")
    return dict(raw)


def validate_layer_plan(raw: object) -> dict:
    """Storyboard agent explicitly identifies each animated character/prop.

    A scene with no independent objects reuses its full master as background.
    The image artist must never invent a movable object during generation.
    """
    if (not isinstance(raw, dict)
            or not {"characters", "movable_props"} <= set(raw)
            or set(raw) - {"characters", "movable_props", "character_parts"}):
        raise SceneLayerError("LAYERS_STORYBOARD_PLAN_REQUIRED")
    seen = set()
    items = {}
    for group, limit in (("characters", MAX_CHARACTERS_PER_SCENE),
                         ("movable_props", MAX_PROPS_PER_SCENE)):
        values = raw[group]
        if not isinstance(values, list) or len(values) > limit:
            raise SceneLayerError("LAYERS_STORYBOARD_COUNT_INVALID")
        normalized = []
        for value in values:
            if not isinstance(value, dict) or set(value) != {"id", "description"}:
                raise SceneLayerError("LAYERS_STORYBOARD_ITEM_INVALID")
            identity = _identifier(value["id"])
            description = value["description"]
            if (identity in seen or not isinstance(description, str)
                    or not 8 <= len(description.strip()) <= 240
                    or any(ord(x) < 32 for x in description)):
                raise SceneLayerError("LAYERS_STORYBOARD_DESCRIPTION_INVALID")
            seen.add(identity)
            normalized.append({"id": identity, "description": description.strip()})
        items[group] = normalized
    parts = raw.get("character_parts", [])
    if not isinstance(parts, list) or len(parts) > MAX_PARTS_PER_SCENE:
        raise SceneLayerError("LAYERS_CHARACTER_PART_COUNT_INVALID")
    result = []
    character_ids = {x["id"] for x in items["characters"]}
    for value in parts:
        if not isinstance(value, dict) or set(value) != {"id", "description", "parent_id"}:
            raise SceneLayerError("LAYERS_CHARACTER_PART_INVALID")
        identity = _identifier(value["id"])
        description = value["description"]
        parent = value["parent_id"]
        if (identity in seen or parent not in character_ids
                or not isinstance(description, str)
                or not 8 <= len(description.strip()) <= 240
                or any(ord(x) < 32 for x in description)):
            raise SceneLayerError("LAYERS_CHARACTER_PART_PARENT_OR_NAME_INVALID")
        seen.add(identity)
        result.append({"id": identity, "description": description.strip(),
                       "parent_id": parent})
    items["character_parts"] = result
    return items


def count_image_requests(manifest: dict) -> int:
    scenes = manifest.get("cenas")
    if not isinstance(scenes, list) or not scenes:
        raise SceneLayerError("LAYERS_MISSING_SCENES")
    if manifest.get("scene_decomposition", {}).get("mode") != MODE:
        raise SceneLayerError("LAYERS_DECOMPOSITION_REQUIRED")
    # 1 master for every scene, 1 background only if there's something to
    # remove, plus one transparent extraction per independent layer.
    total = 0
    for scene in scenes:
        plan = validate_layer_plan(scene.get("layer_plan"))
        items = plan["characters"] + plan["movable_props"]
        total += 1 + (1 if items else 0) + len(items) + len(plan["character_parts"])
    if total > MAX_IMAGE_REQUESTS:
        raise SceneLayerError("LAYERS_MAX_IMAGE_REQUESTS_EXCEEDED")
    return total


def _edit_prompt(*, master: str, role: str, label: str, other_items: list[str],
                 bible: dict) -> str:
    art = (
        f"EDIT THE ACTUAL ATTACHED MASTER SCENE {master} AND NOTHING ELSE. "
        "Use exactly the same framing, perspective, canvas aspect ratio, "
        "character identity, anatomy, colors, lighting, drawing technique, "
        f"brushwork and palette. Locked style: {bible['render_style']}. "
        "The submitted image is the ONLY scene reference. Do not change "
        "character designs or invent any people or objects. "
    )
    if role == "background":
        return art + (
            "OUTPUT ONLY THE CLEAN OPAQUE BACKGROUND, as a full 9:16 PNG. "
            "Remove all independent foreground subjects: " + ", ".join(other_items) +
            ". Inpaint the exact walls, furniture, floor and scenery hidden "
            "behind these subjects. Keep static architectural props intact. "
            "No silhouettes, ghost outlines, transparency, white gaps or cutouts. "
        )
    extra = (
        "The output MUST be a TRUE RGBA PNG with TRANSPARENT pixels outside "
        "the isolated subject — not black/white/checkerboard or simulated alpha. "
        "Keep the original subject at the exact original X/Y position, scale "
        "and pose on a full 9:16 transparent canvas. "
        "Do not crop/center/move, redraw from scratch, or include the room, "
        "furniture, scenery, shadows, any person or other independent prop. "
    )
    if role == "character":
        remove_parts = (" Remove the separately animated appendages from this "
                        "BASE BODY cutout, reconstruct the joint cleanly: " +
                        ", ".join(other_items) + ". " if other_items else "")
        return art + remove_parts + (
            "ISOLATE ONLY THIS CHARACTER from the master: " + label + ". "
            "Preserve exact face, hair, clothes, hands, expression and posture. "
            "Remove separate movable props and fill any masked parts from "
            "the same master scene. "
        ) + extra
    if role == "part":
        return art + (
            "ISOLATE ONLY THIS INDEPENDENT CHARACTER APPENDAGE from the master: " +
            label + ". Preserve its actual pose, colors, clothing and contour. "
            "The parent body and this appendage must NOT overlap in the final "
            "2D sprite composition. Keep the attachment/joint point fixed "
            "in the original coordinates. No other limbs or body. "
        ) + extra
    if role == "prop":
        return art + (
            "ISOLATE ONLY THIS MOVABLE PROP from the master: " + label + ". "
            "Do not include hand, arm or clothing; preserve exact orientation "
            "and visible details from the master. "
        ) + extra
    raise SceneLayerError("LAYERS_INVALID_EXTRACTION_ROLE")


def _save_edit(data: dict, path: Path, *, transparent: bool) -> dict:
    from PIL import Image, ImageOps, UnidentifiedImageError
    try:
        encoded = data["data"][0].get("b64_json") or data["data"][0].get("image_base64")
        if not isinstance(encoded, str) or not 100 < len(encoded) <= 26_000_000:
            raise ValueError()
        if encoded.startswith("data:image/"):
            encoded = encoded.split(",", 1)[1]
        raw = base64.b64decode(encoded, validate=True)
        if not 1000 < len(raw) < 18_000_000:
            raise ValueError()
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            if (image.format not in ("PNG", "JPEG", "WEBP")
                    or image.width < 512 or image.height < 768
                    or image.width * image.height > 18_000_000):
                raise ValueError()
            if transparent and (image.mode not in ("RGBA", "LA", "P")
                                or ("A" not in image.getbands()
                                    and "transparency" not in image.info)):
                raise SceneLayerError("LAYERS_ALPHA_CHANNEL_MISSING")
            # Match master normalized geometry; never flatten the alpha.
            rgba = ImageOps.fit(image.convert("RGBA"), CANVAS,
                                method=Image.Resampling.LANCZOS)
            alpha = rgba.getchannel("A")
            mask = alpha.point(lambda x: 255 if x > 110 else 0)
            covered = sum(mask.histogram()[255:]) / (CANVAS[0] * CANVAS[1])
            if transparent:
                # Reject photos with opaque backgrounds, blank alpha,
                # near-full frame cutouts and tiny specks.
                if not .008 <= covered <= .86:
                    raise SceneLayerError("LAYERS_ALPHA_COVERAGE_INVALID")
                if not 0 < alpha.getextrema()[0] < 255:
                    # Min=0 is expected; this branch handles zero-only.
                    if alpha.getextrema() == (0, 0):
                        raise SceneLayerError("LAYERS_ALPHA_EMPTY")
                transparent_share = sum(alpha.histogram()[:16])/(CANVAS[0]*CANVAS[1])
                if transparent_share < .09:
                    raise SceneLayerError("LAYERS_TRUE_TRANSPARENCY_NOT_FOUND")
            else:
                rgba.putalpha(255)
                covered = 1.
            bounds = mask.getbbox() if transparent else (0, 0, *CANVAS)
            if bounds is None:
                raise SceneLayerError("LAYERS_ALPHA_EMPTY")
            path.parent.mkdir(parents=True, exist_ok=True)
            rgba.save(path, format="PNG")
        if path.stat().st_size < 1000:
            raise ValueError()
        return {"file": path.as_posix(), "sha256": sha256(path.read_bytes()).hexdigest(),
                "alpha_coverage": round(covered, 5),
                "bbox": list(bounds), "transparent": transparent}
    except SceneLayerError:
        raise
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError,
            UnidentifiedImageError):
        raise SceneLayerError("LAYERS_PROVIDER_IMAGE_INVALID") from None


def _validate_asset(directory: Path, asset: dict, *, transparent: bool) -> None:
    from PIL import Image
    target = directory / asset["file"]
    if (target.is_symlink() or not target.is_file()
            or not target.resolve().is_relative_to(directory.resolve())
            or sha256(target.read_bytes()).hexdigest() != asset["sha256"]):
        raise SceneLayerError("LAYERS_IMAGE_PROVENANCE_MISMATCH")
    with Image.open(target) as image:
        image.load()
        if image.format != "PNG" or image.mode != "RGBA" or image.size != CANVAS:
            raise SceneLayerError("LAYERS_ASSET_FORMAT_INVALID")
        alpha = image.getchannel("A")
        if transparent:
            hist = alpha.histogram()
            opaque = sum(hist[111:])/(CANVAS[0]*CANVAS[1])
            empty = sum(hist[:16])/(CANVAS[0]*CANVAS[1])
            if not .008 <= opaque <= .86 or empty < .09:
                raise SceneLayerError("LAYERS_ASSET_TRANSPARENCY_INVALID")
            mask = alpha.point(lambda x: 255 if x > 110 else 0)
            actual_bbox = list(mask.getbbox() or ())
            if (asset.get("bbox") != actual_bbox
                    or abs(asset.get("alpha_coverage", -100) - opaque) > .005):
                raise SceneLayerError("LAYERS_ASSET_ALPHA_METADATA_MISMATCH")
        elif alpha.getextrema() != (255, 255):
            raise SceneLayerError("LAYERS_BACKGROUND_NOT_OPAQUE")


def verify_scene_layers(manifest: dict, directory: Path, doc: dict) -> dict:
    """Verify request provenance/alpha/roles, NOT semantic extraction alignment."""
    if (doc.get("schema") != SCHEMA or doc.get("mode") != MODE
            or doc.get("human_visual_review") is not False
            or doc.get("youtube_upload_approved") is not False):
        raise SceneLayerError("LAYERS_MANIFEST_SCHEMA_INVALID")
    scenes = doc.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != len(manifest["cenas"]):
        raise SceneLayerError("LAYERS_SCENE_LIST_INVALID")
    requests = 0
    for i, (scene, row) in enumerate(zip(manifest["cenas"], scenes), start=1):
        plan = validate_layer_plan(scene["layer_plan"])
        if row.get("scene_id") != scene["id"] or row.get("index") != i:
            raise SceneLayerError("LAYERS_SCENE_ID_MISMATCH")
        master = directory / f"scene-{i}.png"
        if row.get("master_sha256") != sha256(master.read_bytes()).hexdigest():
            raise SceneLayerError("LAYERS_MASTER_DIGEST_MISMATCH")
        elements = plan["characters"] + plan["movable_props"]
        expected_bg = f"scene-{i}/background.png" if elements else f"scene-{i}.png"
        bg = row.get("background", {})
        if (bg.get("file") != expected_bg
                or bg.get("source_master_sha256") != row["master_sha256"]
                or bg.get("origin") != ("codex_proxy_master_scene_edit"
                                      if elements else "codex_proxy_master_scene")):
            raise SceneLayerError("LAYERS_BACKGROUND_NOT_FROM_MASTER")
        if elements:
            _validate_asset(directory, row["background"], transparent=False)
        character_rows = row.get("characters")
        prop_rows = row.get("movable_props")
        part_rows = row.get("character_parts")
        if (not isinstance(character_rows, list) or not isinstance(prop_rows, list)
                or not isinstance(part_rows, list)
                or len(character_rows) != len(plan["characters"])
                or len(prop_rows) != len(plan["movable_props"])
                or len(part_rows) != len(plan["character_parts"])):
            raise SceneLayerError("LAYERS_SUBJECT_COUNT_INVALID")
        requests += 1 + (1 if elements else 0) + len(elements) + len(plan["character_parts"])
        for kind, expected in (("characters", plan["characters"]),
                               ("movable_props", plan["movable_props"]),
                               ("character_parts", plan["character_parts"])):
            for spec, asset in zip(expected, row[kind]):
                file = f"scene-{i}/{kind}/{spec['id']}.png"
                if (asset.get("id") != spec["id"] or asset.get("file") != file
                        or asset.get("source_master_sha256") != row["master_sha256"]
                        or asset.get("origin") != "codex_proxy_master_scene_edit"
                        or (kind == "character_parts" and
                            asset.get("parent_id") != spec["parent_id"])):
                    raise SceneLayerError("LAYERS_SUBJECT_ORIGIN_INVALID")
                _validate_asset(directory, asset, transparent=True)
        if row.get("source") != "video_forge_codex_proxy_master_scene":
            raise SceneLayerError("LAYERS_ORIGIN_INVALID")
    if (doc.get("image_requests") != requests - len(scenes)
            or doc.get("master_image_requests") != len(scenes)
            or doc.get("total_image_requests") != requests
            or requests != count_image_requests(manifest)):
        raise SceneLayerError("LAYERS_REQUEST_COUNT_MISMATCH")
    return {
        "schema": "videoforge/scene-layer-technical-qa/v1",
        "scene_count": len(scenes),
        "layer_image_requests_verified": doc["image_requests"],
        "image_origin_and_hash_verified": True,
        "true_png_transparency_verified": True,
        "full_canvas_dimensions_verified": True,
        "subject_alignment_verified": False,
        "background_ghosting_absence_verified": False,
        "character_identity_verified": False,
        "independent_visual_review": False,
        "approved_for_youtube": False,
        "status": "technical_layers_verified_independent_visual_review_pending",
    }


def generate_scene_layers(manifest: dict, directory: Path, proxy, *,
                          master_assets: list[dict], max_calls: int) -> dict:
    """VideoForge artist derives every layer from its own finished master.

    All requests are prebudgeted before layer generation. Failed/invalid edits
    abort; there is no synthetic local segmentation and no automatic retry.
    """
    config = validate_scene_decomposition(manifest.get("scene_decomposition"))
    planned = count_image_requests(manifest)
    if (planned > max_calls or not isinstance(max_calls, int)
            or isinstance(max_calls, bool) or not 1 <= max_calls <= MAX_IMAGE_REQUESTS):
        raise SceneLayerError("LAYERS_IMAGE_BUDGET_INSUFFICIENT")
    if len(master_assets) != len(manifest["cenas"]):
        raise SceneLayerError("LAYERS_MASTER_COUNT_INVALID")
    bible = manifest["visual_lock"]
    results = []
    requests = 0
    for i, (scene, master_row) in enumerate(zip(manifest["cenas"], master_assets), start=1):
        master = directory / f"scene-{i}.png"
        if (master_row["file"] != master.name or
                master_row["output_sha256"] != sha256(master.read_bytes()).hexdigest()):
            raise SceneLayerError("LAYERS_UNTRUSTED_MASTER")
        plan = validate_layer_plan(scene["layer_plan"])
        things = plan["characters"] + plan["movable_props"]
        original_sha = master_row["output_sha256"]
        row = {
            "scene_id": scene["id"], "index": i, "master": master.name,
            "master_sha256": original_sha,
            "source": "video_forge_codex_proxy_master_scene",
            "characters": [], "movable_props": [], "character_parts": [],
        }
        if things:
            descriptions = [x["description"] for x in things]
            prompt = _edit_prompt(master=scene["id"], role="background",
                                  label="", other_items=descriptions, bible=bible)
            try:
                response = proxy.images_edit_files(prompt=prompt, images=[master],
                                                   model=manifest["modelo_imagem"], n=1)
            except ProxyError as exc:
                raise SceneLayerError("LAYERS_BACKGROUND_EDIT_FAILED") from None
            target = directory / f"scene-{i}/background.png"
            output = _save_edit(response, target, transparent=False)
            row["background"] = {
                "file": target.relative_to(directory).as_posix(),
                "sha256": output["sha256"],
                "origin": "codex_proxy_master_scene_edit",
                "source_master_sha256": original_sha,
            }
            requests += 1
        else:
            row["background"] = {
                "file": master.name, "sha256": original_sha,
                "origin": "codex_proxy_master_scene",
                "source_master_sha256": original_sha,
            }
        for group, role in (("characters", "character"),
                            ("movable_props", "prop"),
                            ("character_parts", "part")):
            for subject in plan[group]:
                appendages = [p["description"] for p in plan["character_parts"]
                              if p["parent_id"] == subject["id"]] if role == "character" else []
                prompt = _edit_prompt(master=scene["id"], role=role,
                                      label=subject["description"], other_items=appendages,
                                      bible=bible)
                try:
                    response = proxy.images_edit_files(prompt=prompt, images=[master],
                                                       model=manifest["modelo_imagem"], n=1,
                                                       background="transparent")
                except ProxyError:
                    raise SceneLayerError("LAYERS_SUBJECT_EDIT_FAILED") from None
                target = directory / f"scene-{i}/{group}/{subject['id']}.png"
                output = _save_edit(response, target, transparent=True)
                row[group].append({
                    "id": subject["id"],
                    **({"parent_id": subject["parent_id"]} if role == "part" else {}),
                    "file": target.relative_to(directory).as_posix(),
                    "sha256": output["sha256"],
                    "origin": "codex_proxy_master_scene_edit",
                    "source_master_sha256": original_sha,
                    "transparent": True,
                    "alpha_coverage": output["alpha_coverage"],
                    "bbox": output["bbox"],
                    "motion_ready_for_review": True,
                    "motion_approved": False,
                })
                requests += 1
        results.append(row)
    document = {
        "schema": SCHEMA, "mode": MODE, "scenes": results,
        "master_image_requests": len(master_assets),
        "image_requests": requests,
        "total_image_requests": requests + len(master_assets),
        "human_visual_review": False,
        "youtube_upload_approved": False,
    }
    # Artista writes generated assets only. Independent technical review is
    # performed by the revisor role after the artist's stage completes.
    (directory / "scene-layers.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return document
