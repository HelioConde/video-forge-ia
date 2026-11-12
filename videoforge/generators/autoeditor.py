"""Operational AutoEditorVideo-derived renderer for VideoForge AI.

Reuses the *real* AutoEditorVideo Remotion MasterShort engine from a pinned
checkout, Edge Neural TTS WordBoundary timing, and the VideoForge Codex Proxy.
Never imports YouTube OAuth/uploaders. Does NOT generate placeholder artwork.
Planning is always offline; production requires explicit local approval.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from videoforge.generators import build_generator_plan, load_generator
from videoforge.production.image_policy import validate_generated_visuals
from videoforge.production.scene_layers import (
    MAX_IMAGE_REQUESTS, SceneLayerError, validate_scene_decomposition,
    validate_layer_plan, count_image_requests, generate_scene_layers,
    verify_scene_layers,
)
from videoforge.production.visual_lock import (
    validate_visual_lock, resolve_reference_image, visual_bible_digest,
    scene_prompt, verify_anchor_trace,
)
from videoforge.production.quality_gate import inspect_media
from videoforge.production.role_events import role_task, CheckReporter
from videoforge.proxy.client import ProxyClient, ProxyError

ROOT = Path(__file__).resolve().parents[2]
FPS = 30
MIN_SHORT_SECONDS = 90
MAX_SHORT_SECONDS = 180
MAX_IMAGES = 12
IMAGE_MODEL = "gpt-image-2"
AUTOEDITOR_COMMIT = "ec85db5bc74455122e4501aba05bd2dd3fd0df2c"
ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VOICE = re.compile(r"^[a-z]{2}-[A-Z]{2}-[A-Za-z0-9]+Neural$")


class AutoEditorBlocked(ValueError):
    """Non-secret deterministic production error."""


def _check_id(value: object, kind: str) -> str:
    if not isinstance(value, str) or len(value) > 70 or not ID.fullmatch(value):
        raise AutoEditorBlocked(f"INVALID_{kind}_ID")
    return value


def _check_text(value: object, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise AutoEditorBlocked(f"INVALID_{label}")
    if any(ord(x) < 32 and x not in "\n\t" for x in value):
        raise AutoEditorBlocked(f"INVALID_{label}_CONTROL_CHARACTER")
    return " ".join(value.strip().split())


def _words(value: str) -> int:
    return len(re.findall(r"\w+", value, flags=re.UNICODE))


def validate_manifest(raw: object, *, root: Path = ROOT) -> dict:
    """Any channel can opt in. No scripts, paths, image bytes or API keys in JSON."""
    if not isinstance(raw, dict) or raw.get("schema") != "videoforge/autoeditor-job/v1":
        raise AutoEditorBlocked("AUTOEDITOR_MANIFEST_SCHEMA_INVALID")
    channel_id = _check_id(raw.get("canal"), "CHANNEL")
    video_id = _check_id(raw.get("id"), "VIDEO")
    channel_file = Path(root) / "canal" / channel_id / "canal.json"
    if channel_file.is_symlink() or not channel_file.is_file():
        raise AutoEditorBlocked("AUTOEDITOR_CHANNEL_NOT_REGISTERED")
    try:
        channel = json.loads(channel_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise AutoEditorBlocked("AUTOEDITOR_CHANNEL_CONFIG_INVALID") from None
    if channel.get("id") != channel_id:
        raise AutoEditorBlocked("AUTOEDITOR_CHANNEL_ID_MISMATCH")
    title = _check_text(raw.get("titulo"), "TITLE", 140)
    description = _check_text(raw.get("descricao"), "DESCRIPTION", 2000)
    lang = raw.get("idioma")
    if lang not in ("pt-BR", "en-US"):
        raise AutoEditorBlocked("AUTOEDITOR_LANGUAGE_NOT_SUPPORTED")
    if lang != channel.get("idioma"):
        raise AutoEditorBlocked("AUTOEDITOR_CHANNEL_LANGUAGE_MISMATCH")
    voice = raw.get("voz", "pt-BR-AntonioNeural" if lang == "pt-BR"
                    else "en-US-AndrewNeural")
    if not isinstance(voice, str) or not VOICE.fullmatch(voice) or not voice.startswith(lang+"-"):
        raise AutoEditorBlocked("AUTOEDITOR_VOICE_INVALID")
    if raw.get("formato") != "short-90s":
        raise AutoEditorBlocked("AUTOEDITOR_ONLY_90S_SHORTS_IMPLEMENTED")
    if raw.get("upload_habilitado") is not False:
        raise AutoEditorBlocked("AUTOEDITOR_UPLOAD_MUST_BE_DISABLED")
    if raw.get("aprovacao_humana_obrigatoria") is not True:
        raise AutoEditorBlocked("AUTOEDITOR_HUMAN_QA_REQUIRED")
    if raw.get("origem_imagens") != "integrated-image-generator":
        raise AutoEditorBlocked("AUTOEDITOR_GENERATOR_IMAGES_REQUIRED")
    if raw.get("modelo_imagem", IMAGE_MODEL) != IMAGE_MODEL:
        raise AutoEditorBlocked("AUTOEDITOR_IMAGE_MODEL_NOT_APPROVED")
    if channel.get("audiencia") == "children" and raw.get("feito_para_criancas") is not True:
        raise AutoEditorBlocked("AUTOEDITOR_KIDS_CLASSIFICATION_REQUIRED")
    if channel.get("audiencia") != "children" and raw.get("feito_para_criancas") is True:
        raise AutoEditorBlocked("AUTOEDITOR_KIDS_CHANNEL_MISMATCH")
    visual_lock = validate_visual_lock(raw.get("visual_lock"))
    decomposition = validate_scene_decomposition(raw.get("scene_decomposition"))
    resolve_reference_image(visual_lock, channel=channel_id, root=root)
    scenes = raw.get("cenas")
    if not isinstance(scenes, list) or not 3 <= len(scenes) <= MAX_IMAGES:
        raise AutoEditorBlocked("AUTOEDITOR_SCENE_COUNT_INVALID")
    output_scenes = []
    seen = set()
    for i, item in enumerate(scenes, start=1):
        if not isinstance(item, dict):
            raise AutoEditorBlocked("AUTOEDITOR_SCENE_INVALID")
        scene_id = _check_id(item.get("id"), "SCENE")
        if scene_id in seen:
            raise AutoEditorBlocked("AUTOEDITOR_DUPLICATED_SCENE_ID")
        seen.add(scene_id)
        output_scenes.append({
            "id": scene_id,
            "narracao": _check_text(item.get("narracao"), "SCENE_NARRATION", 900),
            "prompt_imagem": _check_text(item.get("prompt_imagem"), "IMAGE_PROMPT", 1200),
            "papel": _check_text(item.get("papel", "detail"), "SCENE_ROLE", 60),
            "layer_plan": validate_layer_plan(item.get("layer_plan")),
        })
    if _words(" ".join(s["narracao"] for s in output_scenes)) < 130:
        raise AutoEditorBlocked("AUTOEDITOR_SCRIPT_TOO_SHORT_FOR_90_SECONDS")
    result = {
        "schema": raw["schema"], "canal": channel_id, "id": video_id,
        "titulo": title, "descricao": description, "idioma": lang, "voz": voice,
        "formato": "short-90s", "upload_habilitado": False,
        "aprovacao_humana_obrigatoria": True,
        "feito_para_criancas": channel.get("audiencia") == "children",
        "origem_imagens": "integrated-image-generator",
        "modelo_imagem": IMAGE_MODEL, "visual_lock": visual_lock,
        "scene_decomposition": decomposition, "cenas": output_scenes,
    }
    return result


def load_manifest(path: str | Path, *, root: Path = ROOT) -> dict:
    """Read user editorial plan, not arbitrary executable pipeline."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise AutoEditorBlocked("AUTOEDITOR_JOB_FILE_MISSING")
    if path.stat().st_size > 250_000:
        raise AutoEditorBlocked("AUTOEDITOR_JOB_FILE_TOO_LARGE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise AutoEditorBlocked("AUTOEDITOR_JOB_FILE_INVALID") from None
    return validate_manifest(data, root=root)


def plan(manifest: dict, *, root: Path = ROOT) -> dict:
    definition = load_generator("autoeditor", root=root)
    graph = build_generator_plan(definition, root=root)
    return {
        **graph, "schema": "videoforge/autoeditor-production-plan/v1",
        "channel": manifest["canal"], "video_id": manifest["id"],
        "format": manifest["formato"], "image_model": IMAGE_MODEL,
        "planned_image_calls": count_image_requests(manifest),
        "planned_master_scenes": len(manifest["cenas"]),
        "planned_layer_image_calls": count_image_requests(manifest) - len(manifest["cenas"]),
        "scene_decomposition_mode": manifest["scene_decomposition"]["mode"],
        "visual_reference_mode": "supplied_reference" if manifest["visual_lock"]["reference_path"] else "generate_scene_one_then_edit",
        "expected_duration_seconds": MIN_SHORT_SECONDS,
        "voice_engine": "Edge TTS WordBoundary",
        "renderer": "AutoEditorVideo/motion-remotion/ArquivoOtakuMaster",
        "upstream_commit": AUTOEDITOR_COMMIT,
        "actual_images_generated": 0, "youtube_uploaded": False,
        "note": "Plan only: no API request, TTS, MP4 or upload.",
    }


def _run(args: list[str], *, cwd: Path | None = None, timeout: int = 90):
    try:
        res = subprocess.run(args, cwd=cwd, capture_output=True,
                             timeout=timeout, check=False)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        raise AutoEditorBlocked("AUTOEDITOR_MEDIA_TOOL_FAILED_OR_TIMEOUT") from None
    if res.returncode:
        # No subprocess stdout/stderr printed; can contain remote credentials.
        raise AutoEditorBlocked("AUTOEDITOR_MEDIA_STEP_FAILED")
    return res


async def _edge_audio(script: str, voice: str) -> tuple[bytes, list[dict]]:
    import edge_tts  # installed only on the explicit private render runner
    stream = edge_tts.Communicate(script, voice, boundary="WordBoundary")
    chunks, words = bytearray(), []
    async for event in stream.stream():
        if event.get("type") == "audio":
            chunks.extend(event.get("data", b""))
            if len(chunks) > 40_000_000:
                raise AutoEditorBlocked("AUTOEDITOR_AUDIO_EXCEEDS_LIMIT")
        elif event.get("type") == "WordBoundary":
            start = float(event.get("offset", 0)) / 10_000_000
            end = start + float(event.get("duration", 0)) / 10_000_000
            label = str(event.get("text", "")).strip()
            if end > start >= 0 and label:
                words.append({"start": start, "end": end, "text": label})
    if len(chunks) < 1000 or len(words) < 90:
        raise AutoEditorBlocked("AUTOEDITOR_NO_REAL_TTS_WORD_MARKERS")
    return bytes(chunks), words


def prepare_voice(manifest: dict, out: Path) -> tuple[Path, float, list[dict]]:
    script = " ".join(x["narracao"] for x in manifest["cenas"])
    try:
        audio, words = asyncio.run(_edge_audio(script, manifest["voz"]))
    except AutoEditorBlocked:
        raise
    except Exception:
        # edge_tts remote details must not be printed into public logs.
        raise AutoEditorBlocked("AUTOEDITOR_EDGE_TTS_UNAVAILABLE") from None
    voice = out / "narracao.mp3"
    voice.write_bytes(audio)
    stdout = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=nokey=1:noprint_wrappers=1", str(voice)]).stdout
    try:
        duration = float(stdout.strip())
    except (ValueError, OverflowError):
        raise AutoEditorBlocked("AUTOEDITOR_TTS_DURATION_INVALID") from None
    if not math.isfinite(duration) or not MIN_SHORT_SECONDS <= duration <= MAX_SHORT_SECONDS:
        raise AutoEditorBlocked("AUTOEDITOR_TTS_NOT_90S_TO_180S")
    if words[-1]["end"] > duration + 1.5:
        raise AutoEditorBlocked("AUTOEDITOR_MARKERS_EXCEED_AUDIO_DURATION")
    (out / "marcacoes-voz.json").write_text(json.dumps({
        "source": "real_edge_tts_word_boundary",
        "voice": manifest["voz"], "words": words,
        "script_sha256": sha256(script.encode("utf-8")).hexdigest()
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return voice, duration, words


def real_timing(manifest: dict, words: list[dict], duration: float) -> tuple[list[int], list[dict]]:
    """Map scene splits proportionally to actual word markers, like AutoEditor."""
    if not words or not MIN_SHORT_SECONDS <= duration <= MAX_SHORT_SECONDS:
        raise AutoEditorBlocked("AUTOEDITOR_TIMING_SOURCE_MISSING")
    last, total_frames = -1, round(duration * FPS)
    for word in words:
        if not isinstance(word, dict) or not 0 <= word["start"] < word["end"] <= duration + 1.5:
            raise AutoEditorBlocked("AUTOEDITOR_INVALID_TTS_WORD_MARKER")
        if word["start"] < last:
            raise AutoEditorBlocked("AUTOEDITOR_UNSORTED_TTS_WORD_MARKERS")
        last = word["start"]
    lens = [_words(x["narracao"]) for x in manifest["cenas"]]
    total = sum(lens)
    boundaries = [0]
    running = 0
    for length in lens[:-1]:
        running += length
        at = min(len(words)-1, round(running * len(words) / total))
        boundaries.append(round(float(words[at]["start"]) * FPS))
    boundaries.append(total_frames)
    if any(b-a < FPS for a,b in zip(boundaries, boundaries[1:])):
        raise AutoEditorBlocked("AUTOEDITOR_SCENE_TIMES_TOO_SHORT")
    captions = []
    current = []
    for word in words:
        start = max(0, round(word["start"]*FPS))
        end = min(total_frames, max(start+1, round(word["end"]*FPS)))
        if start >= total_frames:
            continue
        if current and (len(current) >= 3
                        or start - current[0]["startFrame"] > round(1.4 * FPS)):
            captions.append({
                "startFrame": current[0]["startFrame"],
                "endFrame": max(x["endFrame"] for x in current),
                "text": " ".join(x["text"] for x in current),
                "words": current,
            })
            current = []
        current.append({"startFrame": start, "endFrame": end,
                        "text": word["text"]})
    if current:
        captions.append({
            "startFrame": current[0]["startFrame"],
            "endFrame": max(x["endFrame"] for x in current),
            "text": " ".join(x["text"] for x in current),
            "words": current,
        })
    if len(captions) < 25:
        raise AutoEditorBlocked("AUTOEDITOR_REAL_CAPTIONS_INCOMPLETE")
    return boundaries, captions


def generate_images(manifest: dict, out: Path, proxy: ProxyClient, *,
                    max_calls: int) -> list[dict]:
    """Canonical anchor + reference edits, with no fallback or automatic retries.

    Existing reference (if any) seeds scene one through the VideoForge Proxy.
    Otherwise the SAME VideoForge Proxy generates ONE canonical scene one.
    All later scenes are edited from scene-1.png, never text-only generations.
    """
    from PIL import Image, ImageOps
    if len(manifest["cenas"]) > max_calls or not 1 <= max_calls <= MAX_IMAGE_REQUESTS:
        raise AutoEditorBlocked("AUTOEDITOR_GENERATION_BUDGET_INSUFFICIENT")
    bible = validate_visual_lock(manifest.get("visual_lock"))
    # Check every scene for contradictory art direction BEFORE first paid call.
    instructions = [scene_prompt(scene, bible, first=i == 1)
                    for i, scene in enumerate(manifest["cenas"], start=1)]
    source_ref = resolve_reference_image(bible, channel=manifest["canal"], root=ROOT)
    files = []
    for i, scene in enumerate(manifest["cenas"], start=1):
        instruction = instructions[i - 1]
        reference = None
        mode = "canonical_anchor"
        if i == 1 and source_ref is not None:
            reference = source_ref
            mode = "reference_image_edit"
        elif i > 1:
            reference = out / "scene-1.png"
            if not reference.is_file() or reference.is_symlink():
                raise AutoEditorBlocked("AUTOEDITOR_CANONICAL_IMAGE_MISSING")
            mode = "reference_image_edit"
        try:
            if reference is None:
                result = proxy.images_generate({
                    "model": IMAGE_MODEL, "n": 1, "prompt": instruction,
                })
            else:
                result = proxy.images_edit_files(
                    prompt=instruction, images=[reference],
                    model=IMAGE_MODEL, n=1,
                )
        except ProxyError as exc:
            raise AutoEditorBlocked("AUTOEDITOR_IMAGE_PROVIDER_" + str(exc)) from None
        try:
            data = result["data"][0]
            encoded = data.get("b64_json") or data.get("image_base64")
            if not isinstance(encoded, str) or len(encoded) > 26_000_000:
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
                im = ImageOps.fit(image.convert("RGB"), (720, 1280),
                                  method=Image.Resampling.LANCZOS)
            name = f"scene-{i}.png"
            im.save(out / name, format="PNG")
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, OSError):
            raise AutoEditorBlocked("AUTOEDITOR_PROVIDER_IMAGE_INVALID") from None
        record = {
            "scene": i, "file": name, "origin": "codex_proxy_image",
            "generated_by": "video_forge_image_generator",
            "generation_mode": mode,
            "visual_bible_sha256": visual_bible_digest(bible),
            "output_sha256": sha256((out / name).read_bytes()).hexdigest(),
        }
        if i == 1 and source_ref is not None:
            record["source_reference_sha256"] = sha256(source_ref.read_bytes()).hexdigest()
        if i > 1:
            record["anchor_scene"] = 1
            record["anchor_sha256"] = files[0]["output_sha256"]
        files.append(record)
    validate_generated_visuals(files, out, expected_count=len(manifest["cenas"]))
    audit = verify_anchor_trace(files, bible)
    (out / "imagens.json").write_text(json.dumps({
        "schema": "videoforge/generator-only-scenes/v1",
        "provider": "codex_proxy_image", "model": IMAGE_MODEL,
        "assets": files, "visual_audit": audit, "fallback_count": 0,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return files


def build_remotion_props(manifest: dict, duration: float, words: list[dict],
                        *, staging_id: str, layer_document: dict | None = None) -> dict:
    staging_id = _check_id(staging_id, "STAGING")
    cuts, captions = real_timing(manifest, words, duration)
    scenes = []
    for i, (scene, start, end) in enumerate(zip(manifest["cenas"], cuts, cuts[1:]), 1):
        src = f"generated/{staging_id}/scene-{i}.png"
        background = src
        layers = []
        if layer_document is not None:
            row = layer_document["scenes"][i - 1]
            if row["scene_id"] != scene["id"]:
                raise AutoEditorBlocked("AUTOEDITOR_LAYER_SCENE_MISMATCH")
            background = f"generated/{staging_id}/{row['background']['file']}"
            for character in row["characters"]:
                layers.append({
                    "id": character["id"], "role": "front_character",
                    "src": f"generated/{staging_id}/{character['file']}",
                    "z": 20, "alphaCoverage": character["alpha_coverage"],
                    # Never separate arms/hands from an attached movable prop.
                    "heroRisk": .08 if row["movable_props"] else .02,
                    "contactRisk": .30, "anchorX": 50, "anchorY": 80,
                })
            for movable in row["movable_props"]:
                layers.append({
                    "id": movable["id"], "role": "hero_prop",
                    "src": f"generated/{staging_id}/{movable['file']}",
                    "z": 30, "alphaCoverage": movable["alpha_coverage"],
                    # A separate transparent object can be animated later, but
                    # the existing pinned renderer keeps hero props static
                    # rather than inventing motion that may break hand contact.
                })
            if bool(row["characters"] or row["movable_props"]) != bool(layers):
                raise AutoEditorBlocked("AUTOEDITOR_LAYER_GRAPH_INVALID")
        scenes.append({
            "id": scene["id"], "subject": "personagens",
            "startFrame": start, "endFrame": end,
            "background": background, "foreground": background,
            "renderMode": "multilayer" if layers else "master_static",
            **({"layers": layers} if layers else {}),
            "beatRole": "hook" if i == 1 else ("answer" if i == len(cuts)-1 else "detail"),
            "shotType": ("close", "wide", "medium", "detail")[i % 4],
            "transitionStyle": "hard" if i == 1 else "crossfade",
        })
    return {
        "id": manifest["id"], "durationFrames": cuts[-1],
        "audio": f"generated/{staging_id}/voice.mp3",
        "scenes": scenes, "captions": captions, "hook": manifest["titulo"][:70],
        "animationMode": "cinematica",
        "characterPreset": "equilibrado",
        "visualProfile": "original", "editorialProfile": "autoeditor-videoforge",
        "soundCues": [],
    }


def render_remotion(manifest: dict, out: Path, *, motion_root: Path,
                   audio: Path, images: list[dict], duration: float,
                   words: list[dict], job_id: str, reporter: CheckReporter | None = None,
                   layer_document: dict | None = None) -> dict:
    """Run actual AutoEditorVideo MasterShort. Never invoke its upload scripts."""
    motion_root = Path(motion_root).resolve()
    if not (motion_root/"package.json").is_file() or not (motion_root/"src/master-short.tsx").is_file():
        raise AutoEditorBlocked("AUTOEDITOR_REMOTION_SOURCE_MISSING")
    if not (motion_root/"node_modules/.bin/remotion").is_file():
        raise AutoEditorBlocked("AUTOEDITOR_REMOTION_NOT_INSTALLED")
    # Source commit is a contract, not a label inferred from folder names.
    try:
        actual = _run(["git", "-C", str(motion_root.parent), "rev-parse", "HEAD"],
                      timeout=15).stdout.decode("utf-8", "replace").strip()
    except AutoEditorBlocked:
        raise AutoEditorBlocked("AUTOEDITOR_SOURCE_COMMIT_UNVERIFIED") from None
    if actual != AUTOEDITOR_COMMIT:
        raise AutoEditorBlocked("AUTOEDITOR_SOURCE_COMMIT_MISMATCH")
    staging_id = "vf-autoeditor-" + _check_id(job_id, "JOB")
    target = motion_root / "public" / "generated" / staging_id
    if target.exists() or target.is_symlink():
        raise AutoEditorBlocked("AUTOEDITOR_STAGE_ALREADY_EXISTS")
    target.mkdir(parents=True, exist_ok=False)
    try:
        props_file = out/"remotion-props.json"
        with role_task("animador", evidence=(props_file,), reporter=reporter):
            if layer_document is None:
                raise AutoEditorBlocked("AUTOEDITOR_LAYERS_REQUIRED_FOR_RENDER")
            verify_scene_layers(manifest, out, layer_document)
            props = build_remotion_props(manifest, duration, words,
                                          staging_id=staging_id,
                                          layer_document=layer_document)
            props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2)+"\n",
                                  encoding="utf-8")
        shutil.copyfile(audio, target/"voice.mp3")
        for file in images:
            shutil.copyfile(out / file["file"], target / file["file"])
        for row in layer_document["scenes"]:
            for asset in [row["background"], *row["characters"], *row["movable_props"]]:
                source = out / asset["file"]
                destination = target / asset["file"]
                if source.resolve() == (out / row["master"]).resolve():
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
        output = out/"video.mp4"
        with role_task("editor", evidence=(output,), reporter=reporter):
            _run(["npm", "run", "render:master", "--", str(output.resolve()),
                  "--props", str(props_file.resolve()), "--concurrency", "2",
                  "--codec", "h264", "--crf", "21"], cwd=motion_root, timeout=3600)
            media = inspect_media(output)
    finally:
        shutil.rmtree(target, ignore_errors=True)
    if (media["width"], media["height"]) != (1080, 1920) or not 29 <= media["fps"] <= 31:
        raise AutoEditorBlocked("AUTOEDITOR_OUTPUT_FORMAT_INVALID")
    if abs(media["duration_seconds"]-duration) > 2.0:
        raise AutoEditorBlocked("AUTOEDITOR_OUTPUT_VOICE_TIMING_MISMATCH")
    return media


def produce(manifest: dict, *, destination: Path, motion_root: Path,
            job_id: str, max_calls: int, proxy=None) -> dict:
    """Explicit opt-in produces review artifact, never uploads to YouTube."""
    if os.getenv("VIDEOFORGE_AUTOEDITOR_RENDER_AUTHORIZED") != "yes":
        raise AutoEditorBlocked("AUTOEDITOR_EXPLICIT_RENDER_APPROVAL_REQUIRED")
    _check_id(job_id, "JOB")
    dest = Path(destination).resolve()
    if dest.exists():
        raise AutoEditorBlocked("AUTOEDITOR_OUTPUT_DIRECTORY_EXISTS")
    expected_calls = count_image_requests(manifest)
    if (not isinstance(max_calls, int) or isinstance(max_calls, bool)
            or not 1 <= max_calls <= MAX_IMAGE_REQUESTS
            or expected_calls > max_calls):
        raise AutoEditorBlocked("AUTOEDITOR_IMAGE_BUDGET_INVALID")
    client = proxy or ProxyClient(timeout=240)
    accounts = client.accounts()
    records = accounts.get("accounts", []) if isinstance(accounts, dict) else []
    if not any(isinstance(x, dict) and x.get("eligible_now") is True for x in records):
        raise AutoEditorBlocked("AUTOEDITOR_PROXY_ACCOUNT_NOT_ELIGIBLE")
    dest.mkdir(parents=True, mode=0o700)
    reporter = CheckReporter(channel=manifest["canal"])
    with role_task("diretor", evidence=(dest/"plano.json", dest/"briefing.json"), reporter=reporter):
        base_plan = plan(manifest)
        (dest/"plano.json").write_text(json.dumps(base_plan, ensure_ascii=False, indent=2)+"\n",
                                       encoding="utf-8")
        (dest/"briefing.json").write_text(json.dumps({
            "channel": manifest["canal"], "video_id": manifest["id"],
            "title": manifest["titulo"], "description": manifest["descricao"],
            "status": "prepared_for_review", "upload_enabled": False,
        }, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    with role_task("roteirista", evidence=(dest/"roteiro.json", dest/"deduplicacao.json"), reporter=reporter):
        # The script comes from the requested manifest. This worker VALIDATES
        # and records it; it does not autonomously invent a new script.
        (dest/"roteiro.json").write_text(json.dumps({
            "scenes": manifest["cenas"], "originality_not_verified": True,
            "research_not_verified": True, "approved_for_publish": False,
        }, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (dest/"deduplicacao.json").write_text(json.dumps({
            "status": "pending_independent_channel_inventory_review",
            "youtube_history_checked": False, "approved": False,
        }, indent=2)+"\n", encoding="utf-8")
    # TTS first, so an incorrectly paced script does not waste image requests.
    with role_task("narrador", evidence=(dest/"narracao.mp3", dest/"marcacoes-voz.json"), reporter=reporter):
        audio, seconds, words = prepare_voice(manifest, dest)
    with role_task("artista", evidence=(dest/"imagens.json", dest/"scene-layers.json"),
                   reporter=reporter):
        images = generate_images(manifest, dest, client, max_calls=max_calls)
        layers = generate_scene_layers(manifest, dest, client,
                                       master_assets=images, max_calls=max_calls)
    # Reviewer's distinct technical stage checks generated files and alpha.
    # This is NOT approval of artistic alignment, cutout quality or publish.
    with role_task("revisor", evidence=(dest/"qa-camadas.json", dest/"qa-imagens.json"),
                   reporter=reporter):
        layer_qa = verify_scene_layers(manifest, dest, layers)
        (dest/"qa-camadas.json").write_text(
            json.dumps(layer_qa, ensure_ascii=False, indent=2)+"\n",
            encoding="utf-8")
        audit = verify_anchor_trace(images, manifest["visual_lock"])
        (dest/"qa-imagens.json").write_text(json.dumps({
            **audit, "generator_images": len(images),
            "layer_image_requests": layers["image_requests"],
            "true_png_transparency_verified": layer_qa["true_png_transparency_verified"],
            "foreground_background_alignment_verified": False,
            "fallback": 0, "visual_consistency_not_verified": True,
            "publication_blocked_pending_independent_visual_review": True,
        }, indent=2)+"\n", encoding="utf-8")
    media = render_remotion(manifest, dest, motion_root=motion_root, audio=audio,
                           images=images, duration=seconds, words=words,
                           job_id=job_id, reporter=reporter, layer_document=layers)
    props=json.loads((dest/"remotion-props.json").read_text(encoding="utf-8"))
    (dest/"storyboard.json").write_text(json.dumps({
        "source": "remotion_actual_edge_tts_timing",
        "scenes": props["scenes"], "durationFrames": props["durationFrames"],
        "editorial_approved": False,
    }, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (dest/"legendas.json").write_text(json.dumps({
        "source": "real_edge_tts_word_boundary",
        "captions": props["captions"],
    }, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    with role_task("revisor", evidence=(dest/"qa-tecnico.json",), reporter=reporter):
        # This is only an independent TECHNICAL recheck, not editorial approval.
        checked = inspect_media(dest/"video.mp4")
        if checked["sha256"] != media["sha256"]:
            raise AutoEditorBlocked("AUTOEDITOR_TECHNICAL_REVIEW_HASH_MISMATCH")
        (dest/"qa-tecnico.json").write_text(json.dumps({
            "status": "technical_verified", "media": checked,
            "editorial_approved": False, "published": False,
        }, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (dest/"qa-editorial.json").write_text(json.dumps({
        "status": "pending_independent_human_review",
        "originality_not_verified": True, "rights_not_verified": True,
        "visual_consistency_not_verified": True, "voice_quality_not_reviewed": True,
        "youtube_history_not_reviewed": True, "upload_approved": False,
    }, indent=2)+"\n", encoding="utf-8")
    report = {
        "schema": "videoforge/autoeditor-render/v1",
        "status": "rendered_pending_editorial_approval",
        "job_id": job_id, "channel": manifest["canal"], "video_id": manifest["id"],
        "source_renderer": "AutoEditorVideo/Remotion/ArquivoOtakuMaster",
        "source_commit": AUTOEDITOR_COMMIT,
        "voice_source": "edge_tts_real_word_boundary",
        "image_source": "codex_proxy_image",
        "generated_images": len(images),
        "layer_image_requests": layers["image_requests"],
        "image_requests": layers["total_image_requests"],
        "scene_decomposition": manifest["scene_decomposition"]["mode"],
        "generated_layer_files": sum(
            len(row["characters"]) + len(row["movable_props"]) +
            (1 if row["characters"] or row["movable_props"] else 0)
            for row in layers["scenes"]),
        "fallback_images": 0, "media": media,
        "human_approved": False, "youtube_uploaded": False,
        "limitation": "2D RGBA-layer composition; independent prop rigging and human visual QA still pending",
    }
    (dest/"manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                                      encoding="utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="AutoEditorVideo engine (private only)")
    parser.add_argument("--action", choices=("plan", "produce"), default="plan")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--motion-root", type=Path)
    parser.add_argument("--job-id", default="autoeditor-preview")
    parser.add_argument("--max-image-calls", type=int, default=MAX_IMAGES)
    args = parser.parse_args(argv)
    try:
        m = load_manifest(args.manifest)
        if args.action == "plan":
            obj = plan(m)
            output = args.output
            if output.exists():
                raise AutoEditorBlocked("AUTOEDITOR_PLAN_OUTPUT_EXISTS")
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",
                              encoding="utf-8")
            print("AUTOEDITOR_PLAN_ONLY_NO_GENERATION_NO_UPLOAD")
        else:
            if args.motion_root is None:
                raise AutoEditorBlocked("AUTOEDITOR_SOURCE_REQUIRED")
            obj = produce(m, destination=args.output, motion_root=args.motion_root,
                          job_id=args.job_id, max_calls=args.max_image_calls)
            print("AUTOEDITOR_VIDEO_GENERATED_WITH_REAL_PROXY_IMAGES")
            print("AUTOEDITOR_IMAGES_" + str(obj["generated_images"]))
            print("AUTOEDITOR_VIDEO_SHA256_" + obj["media"]["sha256"])
            print("AUTOEDITOR_NO_YOUTUBE_UPLOAD_PENDING_QA")
        return 0
    except (AutoEditorBlocked, ProxyError, ValueError) as exc:
        # Never include untrusted remote exception contents.
        message = str(exc) if isinstance(exc, AutoEditorBlocked) else "AUTOEDITOR_DEPENDENCY_UNAVAILABLE"
        print("AUTOEDITOR_BLOCKED_" + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
