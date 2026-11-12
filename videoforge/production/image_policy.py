"""Enforce generator-only source for every scene before allowing a render.

This validates local artifacts, not a network response signature. The trusted
backend must be the code that received and persisted each image from the image
generation API. A user-supplied manifest cannot establish provenance by itself.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ImageProvenanceError(ValueError):
    pass


def load_image_policy(root: Path = ROOT) -> dict:
    raw = json.loads((Path(root) / "config/production-image-policy.json").read_text(encoding="utf-8"))
    if (raw.get("schema") != "videoforge/production-images/v1"
            or raw.get("mode") != "generator_only"
            or raw.get("assistant_generated_images_allowed") is not False
            or raw.get("local_fallback_allowed") is not False
            or raw.get("on_failure") != "abort_video"):
        raise ImageProvenanceError("INVALID_GENERATOR_ONLY_POLICY")
    return raw


def validate_generated_visuals(assets: list, directory: Path, *,
                               expected_count: int, root: Path = ROOT) -> None:
    """Reject missing, placeholder, invented or tampered images.

    Called only by the private production executor immediately after each
    image-generator API response is saved. Manifest claims are not proof
    when presented by an untrusted actor.
    """
    from PIL import Image, UnidentifiedImageError
    policy = load_image_policy(root)
    if (not isinstance(expected_count, int) or isinstance(expected_count, bool)
            or not 1 <= expected_count <= 40
            or not isinstance(assets, list) or len(assets) != expected_count):
        raise ImageProvenanceError("MISSING_GENERATED_SCENES")
    directory = Path(directory).resolve()
    seen_hashes = set()
    for i, record in enumerate(assets, start=1):
        if (not isinstance(record, dict) or record.get("scene") != i
                or record.get("origin") not in policy["allowed_generators"]
                or record.get("generated_by") != "video_forge_image_generator"
                or record.get("file") != f"scene-{i}.png"):
            raise ImageProvenanceError("UNTRUSTED_VISUAL_OR_FALLBACK")
        path = directory / record["file"]
        if path.is_symlink() or not path.is_file():
            raise ImageProvenanceError("GENERATED_IMAGE_MISSING")
        size = path.stat().st_size
        if size < 1000 or size > 18_000_000:
            raise ImageProvenanceError("GENERATED_IMAGE_SIZE_INVALID")
        digest = sha256(path.read_bytes()).hexdigest()
        if digest != record.get("output_sha256") or digest in seen_hashes:
            raise ImageProvenanceError("GENERATED_IMAGE_DIGEST_INVALID_OR_DUPLICATE")
        seen_hashes.add(digest)
        try:
            with Image.open(path) as img:
                if img.format != "PNG" or img.size != (720, 1280):
                    raise ImageProvenanceError("GENERATED_IMAGE_FORMAT_INVALID")
                img.verify()
        except (OSError, ValueError, UnidentifiedImageError):
            raise ImageProvenanceError("GENERATED_IMAGE_CORRUPT") from None
