"""One-shot live Otaku Multicena research -> script -> layered Remotion preview.

Real verified YouTube history/metrics drive agent topic selection.
The assistant never selects an anime. Two bounded text calls total and at
most 16 image calls, no reruns and NO YouTube publishing. Role evidence
is emitted only around stages that actually execute.
"""
from __future__ import annotations

import argparse
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

from videoforge.channel_agents.team import run_team, EditorialTeamError
from videoforge.channel_agents.manager import ROOT, channel_policy
from videoforge.channel_agents.youtube import (
    YouTubeReadOnly, YouTubeReadError, oauth_access_token,
)
from videoforge.channel_agents.ideation import _parse_chat_json, EditorialIdeationError
from videoforge.generators.autoeditor import (
    AutoEditorBlocked, validate_manifest, count_image_requests, produce,
)
from videoforge.production.role_events import CheckReporter, role_task
from videoforge.proxy.client import ProxyClient, ProxyError

SCHEMA = "videoforge/otaku-multicena-one-shot/v1"
CHANNEL = "otaku-br"
EXPECTED_CHANNEL_ID = "UCXGYTuBYn-0Ziqin5ajKhOw"
MAX_PROXY_CHAT_CALLS = 2
MAX_IMAGE_CALLS = 16
SCENES = 5
MODEL_PREFERENCE = ("gpt-5.4", "gpt-5.3-codex", "gpt-5.4-mini", "gpt-5.2-codex")
ANALYSIS_DAYS = 90
_SHA = re.compile(r"^[a-f0-9]{40}$")
_RUN = re.compile(r"^[0-9]{5,22}$")
_REPO = "HelioConde/video-forge-ia"


class OtakuMissionError(ValueError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def validate_request(value: object) -> dict:
    expected = {
        "schema": SCHEMA,
        "request_id": "otaku-multicena-remotion-test-2026-11-12",
        "channel": CHANNEL,
        "owner_approved": True,
        "youtube_read_only": True,
        "max_proxy_chat_calls": MAX_PROXY_CHAT_CALLS,
        "max_image_calls": MAX_IMAGE_CALLS,
        "independent_remotion_motion": True,
        "require_agent_work_evidence": True,
        "youtube_upload_enabled": False,
        "allow_auto_retry": False,
    }
    if value != expected:
        raise OtakuMissionError("OTAKU_MISSION_REQUEST_NOT_EXACTLY_APPROVED")
    return dict(expected)


def select_model(client: ProxyClient) -> str:
    rows = client.models()
    models = rows.get("data") if isinstance(rows, dict) else None
    available = {row["id"] for row in models if isinstance(row, dict)
                 and isinstance(row.get("id"), str)} if isinstance(models, list) else set()
    selected = next((model for model in MODEL_PREFERENCE if model in available), None)
    if selected is None:
        raise OtakuMissionError("OTAKU_MISSION_SUPPORTED_PROXY_MODEL_UNAVAILABLE")
    return selected


def verified_team_decision(decision: object) -> dict:
    """Never accept an invented topic, mock channel or unreviewed manager pick."""
    if not isinstance(decision, dict):
        raise OtakuMissionError("OTAKU_MISSION_RESEARCH_MISSING")
    chosen = decision.get("chosen_topic")
    deputy = decision.get("deputy")
    if (decision.get("schema") != "videoforge/editorial-team/v1"
            or decision.get("channel") != CHANNEL
            or decision.get("channel_id") != EXPECTED_CHANNEL_ID
            or decision.get("decision_authority") != "Gerente Otaku Multicena"
            or decision.get("topic_provenance") != "codex_proxy_researcher_plus_real_youtube_analytics"
            or decision.get("choices_from_assistant") != 0
            or decision.get("proxy_calls") != 1
            or decision.get("requires_human_editorial_review") is not True
            or decision.get("upload_enabled") is not False
            or not isinstance(decision.get("metrics"), dict)
            or decision["metrics"].get("usable_samples", 0) < 3
            or not isinstance(chosen, dict)
            or not isinstance(deputy, dict)):
        raise OtakuMissionError("OTAKU_MISSION_RESEARCH_NOT_VERIFIED")
    if (not isinstance(chosen.get("id"), str)
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", chosen["id"])
            or not isinstance(chosen.get("anime"), str)
            or chosen["anime"].strip().casefold() == "death note"
            or not isinstance(chosen.get("title"), str)
            or not 10 <= len(chosen["title"]) <= 140
            or not isinstance(chosen.get("angle"), str)
            or not isinstance(chosen.get("genre"), str)
            or not isinstance(chosen.get("format"), str)
            or not isinstance(chosen.get("duration_seconds"), int)
            or not 90 <= chosen["duration_seconds"] <= 180
            or not any(row.get("candidate_id") == chosen["id"] and row.get("accepted") is True
                       for row in deputy.get("candidates", []) if isinstance(row, dict))):
        raise OtakuMissionError("OTAKU_MISSION_TOPIC_NOT_DEPUTY_APPROVED_FOR_90S")
    return dict(chosen)


def _caption_safe(value: object, *, name: str, maximum: int = 480) -> str:
    if not isinstance(value, str) or not 3 <= len(value.strip()) <= maximum:
        raise OtakuMissionError("OTAKU_MISSION_SCRIPT_" + name + "_INVALID")
    if any(ord(x) < 32 for x in value):
        raise OtakuMissionError("OTAKU_MISSION_SCRIPT_CONTROL_CHARACTERS")
    return value.strip()


def build_manifest_from_agent(*, decision: dict, proxy, model: str,
                              run_id: str, root: Path = ROOT) -> dict:
    """One real, strictly validated writing call; no assistant-authored topic."""
    choice = verified_team_decision(decision)
    if not _RUN.fullmatch(run_id):
        raise OtakuMissionError("OTAKU_MISSION_RUN_ID_INVALID")
    context = {
        "selected_topic": choice,
        "channel": "Otaku Multicena",
        "channel_id": EXPECTED_CHANNEL_ID,
        "narration_language": "pt-BR",
        "visual_output": "original illustrated anime analysis, 9:16, 5 storyboard scenes",
        "length": "230-270 Portuguese words total; each scene >=36 words",
        "animated_layers": "one same original visual narrator in all scenes; one symbolic prop in scene 3",
        "motion": "independently moving character PNG in scenes 1,2,4,5; floating prop in scene 3",
        "claimed_analytics": "must come only from selected_topic, never fabricate numbers",
        "truthfulness": "separate creative interpretation from unverified anime facts",
    }
    instruction = (
        "Você é o ROTEIRISTA do VideoForge, NÃO o gerente: a pauta abaixo já "
        "foi escolhida e auditada pelos agents do canal usando YouTube real. "
        "Não mude o anime, tema, título nem duração selecionados. "
        "Faça UM roteiro totalmente original de comentário/análise, com gancho "
        "forte, cinco cenas e encerramento não repetitivo, 230 a 270 palavras "
        "narradas em português brasileiro. Não invente fatos do cânone, métricas, "
        "números, notícias, citações ou fontes. Se for uma hipótese interpretativa, "
        "identifique claramente como interpretação. Nunca copie roteiro de vídeo. "
        "Visuais ilustrados autorais e transformativos, não reproduções de frames "
        "de anime ou logos. Mantenha o MESMO narrador visual original em todas "
        "as cinco cenas; escolha uma bíblia de estilo consistente. Cena 3 DEVE "
        "exibir um símbolo/artefato original, extraível em PNG RGBA transparente "
        "para flutuar de modo independente. As outras cenas exibem o narrador. "
        "Você decide as poses narrativas, mas só movimentos rígidos e seguros. "
        "Retorne SOMENTE JSON: {identity,hair,eyes,wardrobe,accessories,"
        "render_style,descricao,scenes:["
        "{narracao,prompt_imagem,motion},... exatamente 5]}. "
        "motion deve ser um de idle,walk,approach,hop,snuggle,still. "
        "Cena 3 deve ter o símbolo destacável no prompt de arte. "
        "Sem publicação, sem pedido de chamadas de imagem. "
    )
    try:
        response = proxy.chat({
            "model": model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
        })
    except ProxyError:
        raise OtakuMissionError("OTAKU_MISSION_SCRIPTWRITER_PROXY_FAILED") from None
    try:
        draft = _parse_chat_json(response)
    except EditorialIdeationError:
        raise OtakuMissionError("OTAKU_MISSION_SCRIPTWRITER_JSON_INVALID") from None
    scenes = draft.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != SCENES:
        raise OtakuMissionError("OTAKU_MISSION_SCENES_INVALID")
    bible = {
        "schema": "videoforge/visual-bible/v1",
        "mode": "anchor_image_edit", "anchor_scene": 1,
        "style_family": "illustration",
        "character_id": "narrador-original",
        "identity": _caption_safe(draft.get("identity"), name="IDENTITY"),
        "hair": _caption_safe(draft.get("hair"), name="HAIR"),
        "eyes": _caption_safe(draft.get("eyes"), name="EYES"),
        "wardrobe": _caption_safe(draft.get("wardrobe"), name="WARDROBE"),
        "accessories": _caption_safe(draft.get("accessories"), name="ACCESSORIES"),
        "render_style": _caption_safe(draft.get("render_style"), name="STYLE"),
        "require_human_visual_review": True,
    }
    planned_scenes = []
    all_words = 0
    for i, raw in enumerate(scenes, 1):
        if not isinstance(raw, dict) or set(raw) != {"narracao", "prompt_imagem", "motion"}:
            raise OtakuMissionError("OTAKU_MISSION_SCENE_FIELDS_INVALID")
        narration = _caption_safe(raw["narracao"], name="NARRATION", maximum=900)
        image_prompt = _caption_safe(raw["prompt_imagem"], name="IMAGE_PROMPT", maximum=1200)
        words = len(narration.split())
        if not 36 <= words <= 74:
            raise OtakuMissionError("OTAKU_MISSION_SCENE_NARRATION_LENGTH_INVALID")
        all_words += words
        motion = raw["motion"]
        if motion not in ("idle", "walk", "approach", "hop", "snuggle", "still"):
            raise OtakuMissionError("OTAKU_MISSION_INVALID_CHARACTER_MOTION")
        layer_plan = {
            "characters": [{"id": "narrador", "description":
                "O narrador visual original de aparência constante da bíblia do vídeo, exatamente na pose e posição da imagem-mãe"}],
            "movable_props": ([{
                "id": "simbolo", "description":
                "Artefato simbólico original claramente visível nesta cena, extraído da própria imagem-mãe, sem partes do narrador"
            }] if i == 3 else []),
            "character_parts": [],
        }
        cues = [] if motion == "still" else [{
            "id": "narrador", "motion": motion,
            "start": 0.12, "end": 0.82, "distance": 14,
        }]
        if i == 3:
            cues.append({"id": "simbolo", "motion": "float",
                         "start": 0.15, "end": 0.86, "distance": 26})
        planned_scenes.append({
            "id": f"cena-{i}",
            "papel": ("gancho", "contexto", "conflito", "analise", "conclusao")[i-1],
            "narracao": narration,
            "prompt_imagem": image_prompt,
            "layer_plan": layer_plan,
            "motion_plan": {"schema": "videoforge/scene-layer-motion/v1",
                            "cues": cues},
        })
    if not 225 <= all_words <= 290:
        raise OtakuMissionError("OTAKU_MISSION_TOTAL_NARRATION_LENGTH_INVALID")
    raw_manifest = {
        "schema": "videoforge/autoeditor-job/v1",
        "canal": CHANNEL,
        "id": "otaku-remotion-" + run_id,
        "titulo": choice["title"],
        "descricao": _caption_safe(draft.get("descricao"), name="DESCRIPTION", maximum=1700),
        "idioma": "pt-BR", "voz": "pt-BR-AntonioNeural",
        "formato": "short-90s", "feito_para_criancas": False,
        "modelo_imagem": "gpt-image-2",
        "origem_imagens": "integrated-image-generator",
        "aprovacao_humana_obrigatoria": True,
        "upload_habilitado": False,
        "visual_lock": bible,
        "scene_decomposition": {
            "schema": "videoforge/scene-decomposition/v1",
            "mode": "layered_from_master_scene",
            "require_transparent_rgba": True,
            "require_independent_visual_review": True,
        },
        "cenas": planned_scenes,
    }
    try:
        manifest = validate_manifest(raw_manifest, root=root)
    except ValueError:
        raise OtakuMissionError("OTAKU_MISSION_WRITER_OUTPUT_CONTRACT_FAILED") from None
    if count_image_requests(manifest) != MAX_IMAGE_CALLS:
        raise OtakuMissionError("OTAKU_MISSION_IMAGE_BUDGET_MISMATCH")
    if sum(len(x["motion_plan"]["cues"]) for x in manifest["cenas"]) < 4:
        raise OtakuMissionError("OTAKU_MISSION_NOT_ENOUGH_ANIMATIONS")
    if not any("simbolo" in str(x["motion_plan"]["cues"])
               for x in manifest["cenas"]):
        raise OtakuMissionError("OTAKU_MISSION_MISSING_INDEPENDENT_PROP_MOTION")
    return manifest


def reserve_topic_once(*, decision: dict, run_id: str,
                       token: str, env: dict, opener=None) -> str:
    """Create-only GitHub claim before second text call or costly images."""
    topic = verified_team_decision(decision)
    if (env.get("GITHUB_REPOSITORY") != _REPO
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_RUN_ATTEMPT") != "1"
            or env.get("GITHUB_EVENT_NAME") != "push"
            or env.get("GITHUB_ACTOR") != "HelioConde"
            or not _RUN.fullmatch(run_id)
            or not isinstance(token, str) or len(token) < 15):
        raise OtakuMissionError("OTAKU_MISSION_RESERVATION_CONTEXT_INVALID")
    key = (CHANNEL + "|" + topic["anime"].casefold().strip() + "|" +
           topic["title"].casefold().strip() + "|" + topic["angle"].casefold().strip())
    digest = sha256(key.encode("utf-8")).hexdigest()
    location = f"canal/{CHANNEL}/editorial/tentativas/{digest}.json"
    payload = {
        "message": "chore(otaku): reserve selected agent topic " + digest[:12],
        "branch": "main",
        "content": base64.b64encode((json.dumps({
            "schema": "videoforge/otaku-motion-topic-claim/v1",
            "channel": CHANNEL, "source_run_id": run_id,
            "topic_digest": digest,
            "status": "attempt_reserved_no_auto_retry",
            "youtube_upload_approved": False,
        }, separators=(",", ":")) + "\n").encode()).decode(),
    }
    req = Request("https://api.github.com/repos/" + _REPO + "/contents/" + location,
                  method="PUT", data=json.dumps(payload).encode(), headers={
                      "Authorization": "Bearer " + token,
                      "Accept": "application/vnd.github+json",
                      "X-GitHub-Api-Version": "2022-11-28",
                      "Content-Type": "application/json",
                      "User-Agent": "VideoForge-Otaku-OneShot",
                  })
    try:
        with (opener or build_opener(_NoRedirect()).open)(req, timeout=20) as response:
            if response.status != 201:
                raise ValueError()
            result = json.loads(response.read(12000))
        if (result.get("content", {}).get("path") != location or
                not _SHA.fullmatch(result.get("commit", {}).get("sha", ""))):
            raise ValueError()
    except HTTPError as exc:
        if exc.code in (409, 422):
            raise OtakuMissionError("OTAKU_MISSION_TOPIC_ALREADY_RESERVED") from None
        raise OtakuMissionError("OTAKU_MISSION_RESERVATION_HTTP_ERROR") from None
    except (URLError, TimeoutError, OSError, ValueError, TypeError):
        raise OtakuMissionError("OTAKU_MISSION_RESERVATION_UNCERTAIN") from None
    return digest


def run_one_shot(*, proxy: ProxyClient, output: Path, motion_root: Path,
                 run_id: str, token: str, env: dict,
                 save_report: bool = True) -> dict:
    if output.exists() or output.is_symlink() or not _RUN.fullmatch(run_id):
        raise OtakuMissionError("OTAKU_MISSION_OUTPUT_ALREADY_EXISTS_OR_RUN_INVALID")
    # Fail before paid chat calls or TTS if the secured runner cannot create
    # a durable topic reservation or has no eligible Proxy account.
    if (env.get("VIDEOFORGE_OTAKU_MISSION_APPROVED") != "yes"
            or env.get("CHANNEL_IDEATION_APPROVED") != "yes"
            or env.get("VIDEOFORGE_AUTOEDITOR_RENDER_AUTHORIZED") != "yes"
            or env.get("GITHUB_REPOSITORY") != _REPO
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_EVENT_NAME") != "push"
            or env.get("GITHUB_RUN_ATTEMPT") != "1"
            or env.get("GITHUB_ACTOR") != "HelioConde"
            or not isinstance(token, str) or len(token) < 15):
        raise OtakuMissionError("OTAKU_MISSION_NOT_AUTHORIZED")
    accounts = proxy.accounts()
    if not any(isinstance(row, dict) and row.get("eligible_now") is True
               for row in accounts.get("accounts", [])):
        raise OtakuMissionError("OTAKU_MISSION_PROXY_ACCOUNT_UNAVAILABLE")
    model = select_model(proxy)
    manager = channel_policy(CHANNEL)
    if manager["youtube_channel_id"] != EXPECTED_CHANNEL_ID:
        raise OtakuMissionError("OTAKU_MISSION_CHANNEL_CONFIG_CHANGED")
    auth = oauth_access_token(env.get("YOUTUBE_CLIENT_JSON", ""),
                              env.get("YOUTUBE_CHANNEL_TOKEN_JSON", ""))
    youtube = YouTubeReadOnly(access_token=auth, expected_channel_id=EXPECTED_CHANNEL_ID)
    snapshot = youtube.snapshot(days=ANALYSIS_DAYS)
    trends = youtube.trend_signals(["anime curiosidades", "anime análise"], max_queries=2)
    if not snapshot.get("history_complete"):
        raise OtakuMissionError("OTAKU_MISSION_YOUTUBE_HISTORY_INCOMPLETE")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    stage = output / "role-evidence"
    decision = run_team(
        channel=CHANNEL, snapshot=snapshot, trends=trends, client=proxy,
        model=model, stage_dir=stage,
        reporter=CheckReporter(channel=CHANNEL, workflow_kind="editorial"),
    )
    chosen = verified_team_decision(decision)
    (output / "decisao-agents.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    digest = reserve_topic_once(decision=decision, run_id=run_id, token=token, env=env)
    (output / "reserva.json").write_text(json.dumps({
        "status": "reserved_before_script_or_images",
        "topic_sha256": digest, "youtube_uploaded": False,
    }, indent=2)+"\n", encoding="utf-8")
    script_file = output / "roteiro-agente.json"
    with role_task("roteirista", evidence=(script_file,),
                   reporter=CheckReporter(channel=CHANNEL, workflow_kind="autoeditor")):
        manifest = build_manifest_from_agent(
            decision=decision, proxy=proxy, model=model, run_id=run_id)
        script_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n",
                               encoding="utf-8")
    # The AutoEditor stage will reject invalid image budget before the
    # first paid image, perform voice duration preflight and use Remotion.
    report = produce(manifest, destination=output/"video",
                     motion_root=motion_root, job_id="otaku-"+run_id,
                     max_calls=MAX_IMAGE_CALLS, proxy=proxy)
    if (report.get("channel") != CHANNEL or report.get("image_requests") != MAX_IMAGE_CALLS
            or report.get("motion_cues", 0) < 4
            or report.get("youtube_uploaded") is not False
            or report.get("human_approved") is not False):
        raise OtakuMissionError("OTAKU_MISSION_FINAL_REPORT_INVALID")
    (output / "verificacao-missao.json").write_text(json.dumps({
        "schema": "videoforge/otaku-motion-mission-qa/v1",
        "channel": CHANNEL, "channel_identity_verified": True,
        "youtube_history_complete": True,
        "topic_selected_by": "Gerente Otaku Multicena",
        "topic_accepted_by_submanager": True,
        "proxy_text_calls_max": MAX_PROXY_CHAT_CALLS,
        "image_calls_limit": MAX_IMAGE_CALLS,
        "independent_remotion_motion_cues": report["motion_cues"],
        "role_evidence": "GitHub Checks + Commit Status, no simulated activity",
        "mp4_sha256": report["media"]["sha256"],
        "human_visual_review": "pending",
        "publication": "disabled",
    }, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--motion-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.request.is_symlink() or not args.request.is_file():
            raise OtakuMissionError("OTAKU_MISSION_REQUEST_NOT_FOUND")
        validate_request(json.loads(args.request.read_text(encoding="utf-8")))
        env = dict(os.environ)
        run_id = env.get("GITHUB_RUN_ID", "")
        report = run_one_shot(
            proxy=ProxyClient(timeout=240), output=args.output,
            motion_root=args.motion_root, run_id=run_id,
            token=env.get("VF_CHECK_TOKEN", ""), env=env,
        )
        print("OTAKU_MISSION_VIDEO_SHA256_" + report["media"]["sha256"])
        print("OTAKU_MISSION_RESEARCH_YOUTUBE_VERIFIED")
        print("OTAKU_MISSION_REMOTION_LAYERS_RENDERED_NO_UPLOAD")
        return 0
    except (OtakuMissionError, AutoEditorBlocked, EditorialTeamError, YouTubeReadError,
            EditorialIdeationError, ProxyError, ValueError, KeyError, TypeError) as exc:
        # Nothing from the remote model or OAuth response is printed.
        print("OTAKU_MISSION_BLOCKED_" + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
