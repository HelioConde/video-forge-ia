"""Private Otaku preview; mandatory provider-generated scene images, no upload."""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
from pathlib import Path
import re
import subprocess

from videoforge.production.dispatcher import build_plan, mark_verified
from videoforge.production.quality_gate import inspect_media
from videoforge.production.quality_template import review_template
from videoforge.proxy.client import ProxyClient, ProxyError

CHANNEL = "otaku-br"
TOPIC = "O cavaleiro de papel que enfrentou sua propria sombra"
DURATION = 18
LIMIT = 4
BANNED = ("death note", "naruto", "one piece", "dragon ball", "jujutsu kaisen")
SCENE_COUNT = 3


class PilotError(ValueError):
    pass


class CallBudget:
    def __init__(self, limit: int):
        if not 1 <= limit <= LIMIT:
            raise PilotError("INVALID_CALL_LIMIT")
        self.limit, self.sent = limit, 0

    def use(self):
        if self.sent >= self.limit:
            raise PilotError("CALL_LIMIT_EXCEEDED")
        self.sent += 1


def dump(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text_field(value, maximum):
    if not isinstance(value, str):
        raise PilotError("INVALID_TEXT_FIELD")
    value = " ".join(value.split()).strip()
    if not 1 <= len(value) <= maximum or any(x in value.casefold() for x in BANNED):
        raise PilotError("TEXT_TOO_LONG_OR_UNLICENSED_REFERENCE")
    return value


def validate_story(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get("scenes"), list) or len(raw["scenes"]) != 3:
        raise PilotError("STORY_NEEDS_THREE_SCENES")
    tags = raw.get("tags")
    if not isinstance(tags, list) or not 2 <= len(tags) <= 8:
        raise PilotError("INVALID_TAGS")
    return {
        "title": text_field(raw.get("title"), 90),
        "description": text_field(raw.get("description"), 320),
        "tags": [text_field(x, 40) for x in tags],
        "scenes": [{
            "narration": text_field(x.get("narration"), 80),
            "visual_prompt": text_field(x.get("visual_prompt"), 500),
        } for x in raw["scenes"]],
    }


def generate_story(proxy, budget, model):
    budget.use()
    instructions = (
        "Voce e um roteirista de anime FANTASIA AUTORAL, sem franquias. "
        "Crie um teste de 18 segundos sobre um cavaleiro feito de papel "
        "que enfrenta a propria sombra. Sem personagens existentes, noticias, "
        "musica ou fatos nao verificados. Responda SOMENTE um JSON contendo "
        "title (ate 90 chars), description, tags (2-6) e scenes (EXATAMENTE 3), "
        "cada cena com narration (portugues ate 70 chars, cabendo em 6 segundos) "
        "e visual_prompt (ingles, arte original vertical, sem texto). "
        "Gancho, conflito e conclusao. Nao faca upload."
    )
    try:
        raw = proxy.chat({"model": model, "stream": False,
                          "response_format": {"type": "json_object"},
                          "messages": [{"role": "system", "content": instructions},
                                       {"role": "user", "content": TOPIC}]})
        content = raw["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(x.get("text", "") for x in content if isinstance(x, dict))
        if not isinstance(content, str) or len(content) > 16000:
            raise ValueError()
        content = content.strip()
        fence = chr(96)*3
        if content.startswith(fence):
            content = content[3:].lstrip()
            if content.lower().startswith("json"):
                content = content[4:].lstrip()
            content = content.removesuffix(fence).strip()
        return validate_story(json.loads(content)), "codex_proxy"
    except ProxyError as exc:
        raise PilotError("SCRIPT_GENERATOR_UNAVAILABLE_" + str(exc)) from None
    except (PilotError, KeyError, IndexError, TypeError, ValueError):
        raise PilotError("SCRIPT_GENERATION_INVALID_NO_FALLBACK") from None


def command(argv, *, cwd=None, timeout=180):
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise PilotError("MEDIA_EXECUTABLE_MISSING_OR_TIMEOUT") from None
    if result.returncode:
        raise PilotError("MEDIA_COMMAND_FAILED_" + str(result.returncode))


def visuals(proxy, budget, out, story, model):
    """Provider-generated images ONLY; never draw substitutes in the application.

    Missing/invalid image aborts the entire job. Cropping or resizing the
    actual provider output is allowed; creating replacement artwork is not.
    """
    from hashlib import sha256
    from PIL import Image, ImageOps
    from videoforge.production.image_policy import validate_generated_visuals

    scenes = story["scenes"]
    if budget.limit - budget.sent < len(scenes):
        raise PilotError("INSUFFICIENT_BUDGET_FOR_GENERATOR_IMAGES")
    assets = []
    for index, scene in enumerate(scenes):
        budget.use()
        try:
            response = proxy.images_generate({
                "model": model, "n": 1,
                "prompt": scene["visual_prompt"] +
                ". Consistent paper knight; original anime-inspired art, "
                "no existing characters, no logos, no text; cinematic portrait 9:16."
            })
        except ProxyError as exc:
            # ProxyError only contains safe status codes, never credentials.
            raise PilotError("IMAGE_GENERATOR_UNAVAILABLE_" + str(exc)) from None
        try:
            image = response["data"][0]
            encoded = image.get("b64_json") or image.get("image_base64")
            if not isinstance(encoded, str) or len(encoded) > 26000000:
                raise ValueError()
            if encoded.startswith("data:image/"):
                encoded = encoded.split(",", 1)[1]
            blob = base64.b64decode(encoded, validate=True)
            if not 1000 < len(blob) < 18000000:
                raise ValueError()
            frame = Image.open(io.BytesIO(blob))
            frame.load()
            if frame.width * frame.height > 18000000 or frame.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValueError()
            frame = ImageOps.fit(frame.convert("RGB"), (720, 1280),
                                 method=Image.Resampling.LANCZOS)
            filename = f"scene-{index+1}.png"
            frame.save(out/filename, format="PNG")
        except (KeyError, IndexError, AttributeError, ValueError, OSError, TypeError):
            raise PilotError("IMAGE_GENERATOR_RETURNED_INVALID_MEDIA") from None
        assets.append({
            "scene": index+1, "file": filename, "origin": "codex_proxy_image",
            "generated_by": "video_forge_image_generator",
            "output_sha256": sha256((out/filename).read_bytes()).hexdigest(),
        })
    validate_generated_visuals(assets, out, expected_count=len(scenes))
    dump(out/"assets.json", {"schema": "videoforge/generator-only-scenes/v1",
                            "assets": assets, "ai_image_count": len(assets),
                            "local_image_fallbacks": 0})
    return assets


def thumbnail(out):
    from PIL import Image, ImageDraw, ImageFont
    frame = Image.open(out/"scene-1.png").crop((0, 250, 720, 970)).convert("RGB")
    d = ImageDraw.Draw(frame, "RGBA")
    d.rectangle((20, 468, 700, 708), fill=(6, 13, 25, 220))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    d.text((32, 495), "CAVALEIRO", font=font, fill="white")
    d.text((32, 576), "DE PAPEL", font=font, fill=(255, 228, 150))
    frame.save(out/"thumbnail.png")


def audio_subtitles(out, story):
    pieces, captions = [], []
    for i, row in enumerate(story["scenes"], 1):
        raw = out/f"voice-{i}.wav"
        padded = out/f"voice-{i}-padded.wav"
        command(["espeak-ng", "-v", "pt-br", "-s", "165", "-a", "165",
                 "-w", str(raw), row["narration"]], timeout=35)
        command(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(raw),
                 "-af", "apad", "-t", "6", "-ar", "44100", "-ac", "1",
                 "-c:a", "pcm_s16le", str(padded)], timeout=45)
        pieces.append(padded)
        a, b = (i-1)*6, i*6
        captions.append(f"{i}\n00:00:{a:02d},000 --> 00:00:{b:02d},000\n"
                        f"{row['narration']}\n")
    (out/"legendas.srt").write_text("\n".join(captions), encoding="utf-8")
    playlist = out/"audio-list.txt"
    playlist.write_text("".join(f"file '{p}'\n" for p in pieces), encoding="utf-8")
    command(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat",
             "-safe", "0", "-i", str(playlist), "-t", "18", "-ar", "44100",
             "-ac", "1", "-c:a", "pcm_s16le", str(out/"audio-master.wav")])
    (out/"narracao.wav").write_bytes((out/"audio-master.wav").read_bytes())


def render(out):
    clips = []
    for i in range(1, 4):
        clip = out/f"clip-{i}.mp4"
        command(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-loop", "1",
                 "-framerate", "24", "-i", str(out/f"scene-{i}.png"), "-t", "6",
                 "-vf", "zoompan=z='min(zoom+0.0008,1.11)':d=1:"
                        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                        "s=720x1280:fps=24,format=yuv420p",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-r", "24",
                 "-an", str(clip)], timeout=170)
        clips.append(clip)
    concat = out/"video-list.txt"
    concat.write_text("".join(f"file '{x}'\n" for x in clips), encoding="utf-8")
    command(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat",
             "-safe", "0", "-i", str(concat), "-c", "copy", str(out/"silent.mp4")])
    command(["ffmpeg", "-nostdin", "-loglevel", "error", "-y",
             "-i", str(out/"silent.mp4"), "-i", str(out/"audio-master.wav"),
             "-map", "0:v:0", "-map", "1:a:0", "-vf", "subtitles=legendas.srt",
             "-t", "18", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
             "-movflags", "+faststart", str(out/"video.mp4")], cwd=out, timeout=200)


STAGE_FILES = {
    "briefing": "briefing.json", "pesquisa": "pesquisa.json",
    "roteiro": "roteiro.json", "titulo": "titulo.json",
    "descricao": "descricao.md", "tags": "tags.json",
    "storyboard": "storyboard.json", "thumbnail": "thumbnail.png",
    "narracao": "narracao.wav", "visuais": "assets.json",
    "animacao": "animacoes.json", "legendas": "legendas.srt",
    "audio": "audio-master.wav", "edicao": "video.mp4",
    "qa_tecnico": "qa-tecnico.json",
}


def produce(out: Path, job_id: str, *, max_calls=LIMIT, model="gpt-6.1-sol",
            image_model="gpt-image-2", client=None):
    if os.getenv("VIDEOFORGE_PILOT_APPROVED") != "yes":
        raise PilotError("OWNER_APPROVAL_REQUIRED")
    if not re.fullmatch("[A-Za-z0-9_-]{3,64}", job_id):
        raise PilotError("JOB_ID_INVALID")
    out = out.resolve()
    if out.exists():
        raise PilotError("OUTPUT_MUST_NOT_EXIST")
    budget = CallBudget(max_calls)
    # Reserve one chat call + a generator call per image; never degrade.
    if max_calls < 1 + SCENE_COUNT:
        raise PilotError("BUDGET_REQUIRES_GENERATOR_IMAGES")
    proxy = client or ProxyClient(timeout=240)
    account_data = proxy.accounts()
    accounts = account_data.get("accounts", []) if isinstance(account_data, dict) else []
    if not any(isinstance(x, dict) and x.get("eligible_now") is True for x in accounts):
        raise PilotError("NO_ELIGIBLE_PROXY_ACCOUNT")
    out.mkdir(parents=True, mode=0o700)
    plan = build_plan({"id": job_id, "canal": CHANNEL, "tema": TOPIC,
                       "duracao_segundos": DURATION})
    story, source = generate_story(proxy, budget, model)
    dump(out/"briefing.json", {"channel": CHANNEL, "topic": TOPIC,
                               "test_only": True, "publication_enabled": False})
    dump(out/"pesquisa.json", {"fictional_original": True, "external_facts_used": 0,
                              "youtube_history_checked": False,
                              "requires_originality_review": True})
    dump(out/"roteiro.json", {**story, "source": source, "seconds": DURATION})
    dump(out/"titulo.json", {"title": story["title"], "origin": source})
    (out/"descricao.md").write_text(story["description"]+"\n", encoding="utf-8")
    dump(out/"tags.json", {"tags": story["tags"]})
    dump(out/"storyboard.json", {"seconds": DURATION,
        "scenes": [{"start": i*6, "seconds": 6, **x} for i, x in enumerate(story["scenes"])]})
    assets = visuals(proxy, budget, out, story, image_model)
    thumbnail(out)
    dump(out/"animacoes.json", {"technique": "ken_burns_camera",
                                "note": "not character rigging", "scenes": 3})
    audio_subtitles(out, story)
    render(out)
    media = inspect_media(out/"video.mp4")
    if min(media["width"], media["height"]) < 720 or abs(media["duration_seconds"]-18) > 2:
        raise PilotError("MEDIA_TECHNICAL_CHECK_FAILED")
    dump(out/"qa-tecnico.json", {"status": "technical_media_verified",
                                 "media": media, "voice_quality": "not_human_reviewed"})
    dump(out/"qa-conteudo.json", {
        "status": "pending_independent_editorial_review",
        "rights_review": False, "originality_review": False,
        "visual_review": False, "youtube_history_review": False})
    dump(out/"quality-review-template.json", review_template(plan))
    for task, name in STAGE_FILES.items():
        mark_verified(plan, task, evidence_path=out/name)
    plan["mode"] = "pilot_preview_executed"
    plan["execution_enabled"] = True
    plan["publishing_enabled"] = False
    plan["pilot_pending"] = ["qa_conteudo", "aprovacao", "publicacao"]
    dump(out/"plano-executado.json", plan)
    manifest = {
        "schema": "videoforge/pilot-first-video/v1", "channel": CHANNEL,
        "job_id": job_id, "status": "preview_generated_pending_editorial_review",
        "format": "technical_preview_not_short",
        "story_origin": source,
        "ai_image_count": sum(x["origin"] == "codex_proxy_image" for x in assets),
        "local_image_fallbacks": 0,
        "visual_provenance": "generator_only_verified",
        "generative_calls": budget.sent, "max_calls": budget.limit,
        "verified_stages": list(STAGE_FILES),
        "media": media, "human_approved": False, "youtube_uploaded": False,
        "limitations": ["robotic_offline_tts", "no_full_channel_inventory",
                        "no_independent_editorial_review", "no_character_rigging"],
    }
    dump(out/"manifest.json", manifest)
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--job-id", required=True)
    ap.add_argument("--max-calls", type=int, default=4)
    args = ap.parse_args(argv)
    try:
        manifest = produce(args.output, args.job_id, max_calls=args.max_calls)
    except (PilotError, ProxyError, ValueError) as exc:
        print("PILOT_FAILED_" + str(exc))
        return 1
    print("PILOT_VIDEO_RENDERED_SHA256_VERIFIED")
    print("VERIFIED_STAGE_COUNT_" + str(len(manifest["verified_stages"])))
    print("GENERATIVE_REQUEST_COUNT_" + str(manifest["generative_calls"]))
    print("GENERATED_IMAGE_COUNT_" + str(manifest["ai_image_count"]))
    print("NO_YOUTUBE_UPLOAD_EDITORIAL_QA_PENDING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
