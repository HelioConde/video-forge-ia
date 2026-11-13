"""Fail-closed offline readiness for the first agent-led Otaku Multicena Short.

This checks whether the editorial reservation, production manifest and
explicit image-call allowance exist. It does NOT authenticate a private
editorial workflow, check provider quota or turn a sample script into
an autonomous agent result. It NEVER calls Proxy, YouTube or any media API.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from videoforge.generators.autoeditor import (
    MAX_IMAGE_REQUESTS, AutoEditorBlocked, load_manifest, plan,
)

ROOT = Path(__file__).resolve().parents[2]
CHANNEL = "otaku-br"
SAMPLE = "geradores/autoeditor/exemplo-manifesto.json"
LEDGER = "canal/otaku-br/editorial/reservas.json"


class ReadinessError(ValueError):
    pass


def _manifest_path(value: str, *, root: Path) -> Path:
    if not isinstance(value, str) or len(value) > 230 or not value:
        raise ReadinessError("OTAKU_MANIFEST_PATH_INVALID")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ReadinessError("OTAKU_MANIFEST_PATH_INVALID")
    path = root / relative
    resolved = path.resolve()
    if (not resolved.is_relative_to(root.resolve())
            or resolved.is_symlink() or path.is_symlink()
            or not (
                relative.as_posix() == SAMPLE
                or (len(relative.parts) >= 4
                    and relative.parts[:3] == ("canal", "otaku-br", "videos"))
            )):
        raise ReadinessError("OTAKU_MANIFEST_PATH_NOT_ALLOWED")
    return resolved


def _ledger(root: Path) -> list[dict]:
    path = root / LEDGER
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 150_000:
        raise ReadinessError("OTAKU_RESERVATION_LEDGER_UNSAFE")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise ReadinessError("OTAKU_RESERVATION_LEDGER_INVALID") from None
    if (not isinstance(document, dict)
            or document.get("schema") != "videoforge/channel-topic-reservations/v1"
            or document.get("channel") != CHANNEL
            or document.get("channel_id") != "UCXGYTuBYn-0Ziqin5ajKhOw"
            or not isinstance(document.get("entries"), list)
            or len(document["entries"]) > 500
            or any(not isinstance(x, dict) for x in document["entries"])):
        raise ReadinessError("OTAKU_RESERVATION_LEDGER_INVALID")
    return document["entries"]


def assess(*, root: Path = ROOT, manifest_path: str = SAMPLE,
           max_image_calls: int = 12) -> dict:
    """Report concrete gaps, not a promise of quota, topic or generated video."""
    if (not isinstance(max_image_calls, int)
            or isinstance(max_image_calls, bool)
            or not 0 <= max_image_calls <= MAX_IMAGE_REQUESTS):
        raise ReadinessError("OTAKU_IMAGE_CALL_LIMIT_INVALID")

    entries = _ledger(root)
    # A ledger entry is NOT sufficient evidence of a real editorial
    # decision; the private workflow and AES-GCM source must be checked.
    claimed_approved = [
        x for x in entries
        if x.get("status") == "approved_reserved"
        and x.get("human_approved") is True
    ]
    is_template = manifest_path == SAMPLE
    # A checked-in draft is not an agent-selected production manuscript.
    is_provisional = False
    path = _manifest_path(manifest_path, root=root)
    if not path.is_file():
        if is_template:
            raise ReadinessError("OTAKU_EXAMPLE_MANIFEST_MISSING")
        manifest_present = False
        manifest_valid = False
        required = None
        expected_duration = None
    else:
        manifest_present = True
        try:
            manifest = load_manifest(path, root=root)
            # Explicit draft IDs remain drafts even if structurally valid and
            # the user-authorized image budget covers every planned request.
            is_provisional = (not is_template and
                              manifest["id"].endswith("-rascunho"))
            if manifest.get("canal") != CHANNEL:
                raise ReadinessError("OTAKU_MANIFEST_CHANNEL_INVALID")
            graph = plan(manifest, root=root)
            required = graph["planned_image_calls"]
            expected_duration = graph["expected_duration_seconds"]
            manifest_valid = True
        except AutoEditorBlocked as exc:
            # Only report fixed local reason, not untrusted input strings.
            raise ReadinessError("OTAKU_MANIFEST_INVALID_" + str(exc)) from None
        if not isinstance(required, int) or required < 3:
            raise ReadinessError("OTAKU_PLAN_IMAGE_COUNT_INVALID")

    blockers = []
    if not claimed_approved:
        blockers.append("NO_HUMAN_APPROVED_EDITORIAL_RESERVATION")
    # This offline job cannot read confidential YouTube analytics or decrypt
    # and attest the selected topic. It MUST NOT infer approval from JSON.
    blockers.append("NO_AUTHENTICATED_AGENT_DECISION_HANDOFF")
    if not manifest_present:
        blockers.append("NO_90_SECOND_RENDER_MANIFEST")
    elif is_template:
        blockers.append("SAMPLE_STORY_NOT_SELECTED_BY_TEAM")
    elif is_provisional:
        blockers.append("PROVISIONAL_DRAFT_NOT_SELECTED_BY_TEAM")
    # A valid manuscript still needs independent evidence it came from
    # approved agent output; textual similarity alone is insufficient.
    blockers.append("AGENT_SCRIPT_AND_STORYBOARD_PROVENANCE_NOT_VERIFIED")
    if required is not None and required > max_image_calls:
        blockers.append("IMAGE_CALL_BUDGET_BELOW_PLAN")
    if max_image_calls == 0:
        blockers.append("NO_EXPLICIT_IMAGE_BUDGET")
    blockers.append("PROXY_TEXT_AND_IMAGE_QUOTA_NOT_VERIFIED")
    blockers.append("HUMAN_RENDER_APPROVAL_NOT_RECORDED")

    return {
        "schema": "videoforge/otaku-team-video-readiness/v1",
        "channel": CHANNEL,
        "status": "blocked",
        "can_render_now": False,
        "candidate_manifest": (
            "sample" if is_template else
            "provisional_draft" if is_provisional else
            "supplied_not_proven" if manifest_present else "missing"
        ),
        "manifest_structurally_valid": manifest_valid,
        "target_duration_seconds": expected_duration,
        "planned_image_requests": required,
        "explicit_image_call_limit": max_image_calls,
        "budget_shortfall": max(0, required-max_image_calls) if required is not None else None,
        "reservation_claims_found": len(claimed_approved),
        "private_source_verified": False,
        "script_provenance_verified": False,
        "quota_verified": False,
        "human_render_approved": False,
        "blockers": blockers,
        "proxy_calls": 0,
        "youtube_calls": 0,
        "images_generated": 0,
        "videos_rendered": 0,
        "videos_uploaded": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Otaku video readiness, no generation.")
    parser.add_argument("--manifest", default=SAMPLE)
    parser.add_argument("--max-image-calls", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = assess(manifest_path=args.manifest, max_image_calls=args.max_image_calls)
        if args.output.exists() or args.output.is_symlink():
            raise ReadinessError("OTAKU_READINESS_OUTPUT_EXISTS")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n",
                               encoding="utf-8")
        print("OTAKU_VIDEO_NOT_READY_" + str(len(report["blockers"])) + "_BLOCKERS")
        print("OTAKU_READINESS_ZERO_PROXY_ZERO_IMAGES_ZERO_UPLOADS")
        return 0
    except ReadinessError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
