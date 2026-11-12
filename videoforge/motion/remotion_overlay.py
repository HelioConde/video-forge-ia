"""Install a checked, small VideoForge sprite-motion overlay into pinned Remotion.

No downloads, shell injection, package changes or upstream repo mutation.
The checkout remains pinned by git commit; copy only the trusted TS file into
its temporary Actions workspace, then patch a few verified source anchors.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
TS = ROOT / "videoforge/motion/videoforge-motion.ts"
OVERLAY_NAME = "videoforge-motion.ts"


class MotionOverlayError(ValueError):
    """Render-blocking, public-safe source mismatch."""


def apply_motion_overlay(motion_root: Path, *, overlay_source: Path = TS) -> str:
    motion_root = Path(motion_root)
    destination = motion_root / "src"
    target = destination / "master-short.tsx"
    module = destination / OVERLAY_NAME
    if (not target.is_file() or target.is_symlink()
            or not (destination/"character-idle.ts").is_file()
            or not (destination/"pose-timeline.ts").is_file()
            or not overlay_source.is_file() or overlay_source.is_symlink()):
        raise MotionOverlayError("VIDEOFORGE_MOTION_REMOTION_SOURCE_MISSING")
    original = target.read_text(encoding="utf-8")
    module_text = overlay_source.read_text(encoding="utf-8")
    if len(module_text) < 500 or len(module_text) > 30_000:
        raise MotionOverlayError("VIDEOFORGE_MOTION_MODULE_INVALID")
    import_marker = "import {meshFrameIndex} from './pose-timeline';"
    role_marker = "  meshFrames?:{fps:number;frames:string[]}"
    transform_marker = """          const transform=!staticLayer && pose.enabled
            ? 'translate('+pose.translateX.toFixed(3)+'px,'+
              pose.translateY.toFixed(3)+'px) rotate('+pose.rotateDeg.toFixed(4)+
              'deg)'
            : undefined;"""
    style_marker = "            transform,\n            transformOrigin:(layer.anchorX ?? 50)+'% '+(layer.anchorY ?? 80)+'%',"
    targets = [import_marker, role_marker, transform_marker, style_marker]
    if any(original.count(x) != 1 for x in targets):
        raise MotionOverlayError("VIDEOFORGE_MOTION_UPSTREAM_VERSION_UNSUPPORTED")
    if "videoforge-motion" in original:
        raise MotionOverlayError("VIDEOFORGE_MOTION_ALREADY_INSTALLED")
    changed = original.replace(
        import_marker, import_marker +
        "\nimport {videoForgeMotionAtFrame,VideoForgeMotionCue} from './videoforge-motion';"
    ).replace(
        role_marker, "  motion?:VideoForgeMotionCue[];\n" + role_marker
    ).replace(
        transform_marker,
        """          // The VideoForge animator owns explicit layer motion; no
          // whole-character pose approximation may override it.
          const authored=layer.motion?.length
            ?videoForgeMotionAtFrame(layer.motion,frame,scene.startFrame,scene.endFrame)
            :undefined;
          const transform=authored?.transform ?? (!staticLayer && pose.enabled
            ? 'translate('+pose.translateX.toFixed(3)+'px,'+
              pose.translateY.toFixed(3)+'px) rotate('+pose.rotateDeg.toFixed(4)+
              'deg)'
            : undefined);"""
    ).replace(
        style_marker,
        "            transform,opacity:authored?.opacity,\n"
        "            transformOrigin:(layer.anchorX ?? 50)+'% '+(layer.anchorY ?? 80)+'%',"
    )
    if changed == original or changed.count("videoForgeMotionAtFrame(") != 1:
        raise MotionOverlayError("VIDEOFORGE_MOTION_PATCH_INVALID")
    if module.exists():
        raise MotionOverlayError("VIDEOFORGE_MOTION_OVERLAY_ALREADY_EXISTS")
    # The renderer lives in an ephemeral worktree. It can be overwritten
    # safely only after all known anchors are validated.
    module.write_text(module_text, encoding="utf-8")
    target.write_text(changed, encoding="utf-8")
    return sha256(module_text.encode("utf-8")).hexdigest()
