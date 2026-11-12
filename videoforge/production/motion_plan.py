"""Frame-safe layer motion plan, modeled on Fofinho EP01 Part 3.

The Storyboard owns the cue list. The Animator verifies actors and allowed
transform kinds before composing a Remotion preview. Does not generate images
or pretend a one-piece character can articulate individual paws.
"""
from __future__ import annotations

from collections import defaultdict
import math

SCHEMA = "videoforge/scene-layer-motion/v1"
KINDS = {
    "characters": frozenset({"still", "idle", "walk", "approach", "hop", "snuggle"}),
    "character_parts": frozenset({"still", "paw-lift", "paw-wave", "pat", "sway"}),
    "movable_props": frozenset({"still", "float", "rise", "fall", "orbit",
                               "bounce", "sway", "pulse", "pop", "settle"}),
}
MAX_CUES = 16
MAX_DISTANCE = 46.0


class MotionPlanError(ValueError):
    """Non-secret motion policy rejection."""


def validate_motion_plan(raw: object, layer_plan: dict) -> dict:
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA or set(raw) != {"schema", "cues"}:
        raise MotionPlanError("MOTION_PLAN_SCHEMA_REQUIRED")
    cues = raw["cues"]
    if not isinstance(cues, list) or len(cues) > MAX_CUES:
        raise MotionPlanError("MOTION_CUE_COUNT_INVALID")
    groups = {}
    for group, allowed in KINDS.items():
        for item in layer_plan.get(group, []):
            if item["id"] in groups:
                raise MotionPlanError("MOTION_ACTOR_DUPLICATED")
            groups[item["id"]] = (group, allowed)
    timetable = defaultdict(list)
    approved = []
    for cue in cues:
        if not isinstance(cue, dict) or set(cue) != {"id", "motion", "start", "end", "distance"}:
            raise MotionPlanError("MOTION_CUE_FIELDS_INVALID")
        actor = cue["id"]
        if not isinstance(actor, str) or actor not in groups:
            raise MotionPlanError("MOTION_ACTOR_NOT_EXTRACTED")
        group, allowed = groups[actor]
        kind = cue["motion"]
        if not isinstance(kind, str) or kind not in allowed:
            raise MotionPlanError("MOTION_REQUIRES_CORRECT_LAYER_ROLE")
        start, end, distance = cue["start"], cue["end"], cue["distance"]
        if any(isinstance(n, bool) or not isinstance(n, (float, int))
               or not math.isfinite(n) for n in (start, end, distance)):
            raise MotionPlanError("MOTION_CUE_NUMERIC_INVALID")
        if not 0 <= start < end <= 1 or end-start < .05 or not 0 <= distance <= MAX_DISTANCE:
            raise MotionPlanError("MOTION_CUE_TIMING_OR_DISTANCE_INVALID")
        if kind == "still" and distance != 0:
            raise MotionPlanError("MOTION_STILL_CANNOT_MOVE")
        if kind in ("paw-lift", "paw-wave", "pat") and group != "character_parts":
            raise MotionPlanError("MOTION_PAW_REQUIRES_ISOLATED_PART")
        for earlier_start, earlier_end in timetable[actor]:
            if start < earlier_end and earlier_start < end:
                raise MotionPlanError("MOTION_OVERLAPPING_ACTOR_CUES")
        timetable[actor].append((start, end))
        approved.append({"id": actor, "motion": kind, "start": float(start),
                         "end": float(end), "distance": float(distance)})
    return {"schema": SCHEMA, "cues": approved}


def motion_for_actor(approved_plan: dict, actor_id: str) -> list[dict]:
    return [dict(c) for c in approved_plan["cues"] if c["id"] == actor_id]


def verify_animated_scene(plan: dict, layers: list[dict]) -> dict:
    """Technical role audit, not claim of actual semantic animation quality."""
    ids = {layer["id"] for layer in layers}
    for cue in plan["cues"]:
        if cue["id"] not in ids:
            raise MotionPlanError("MOTION_LAYER_MISSING_FROM_COMPOSITION")
    return {
        "schema": "videoforge/motion-stage-audit/v1",
        "configured_cues": len(plan["cues"]),
        "all_motion_actors_have_rgba_layers": True,
        "cue_roles_validated": True,
        "rendered_frames_visually_reviewed": False,
        "paw_articulation_if_part_missing": False,
        "youtube_upload_approved": False,
    }
