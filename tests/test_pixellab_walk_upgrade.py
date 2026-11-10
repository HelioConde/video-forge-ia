"""Não confundir animações Walking dos estados walk e Idle."""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from PIL import Image

from scripts.refresh_pixellab_walk import replace_walk, DIRECTIONS

CID = "test-pixellab-character"
IDENTITY = hashlib.sha256(CID.encode()).hexdigest()


def make_export(work: Path, *, include_walk=True, include_idle=True,
                missing=None, walk_state_name="walk"):
    root = work / "alex"
    root.mkdir()
    old_image = Image.new("RGBA", (704, 704), (50, 50, 50, 255))
    old_bytes = io.BytesIO()
    old_image.save(old_bytes, "PNG")
    original = old_bytes.getvalue()
    (root / "walk.png").write_bytes(original)
    (root / "manifest.json").write_text(json.dumps({
        "schema": "videoforge/pixellab-agent-atlas/v1",
        "character": "alex", "frames": 4,
        "frameWidth": 88, "frameHeight": 88,
        "directions": list(DIRECTIONS),
        "motions": {"walk": {
            "file": "walk.png", "width": 704, "height": 704, "frames": 8,
            "sourceAnimation": "walking",
            "sha256": hashlib.sha256(original).hexdigest()
        }}
    }))
    target = work / "export.zip"
    with ZipFile(target, "w") as archive:
        archive.writestr("metadata.json", json.dumps({
            "states": [{"character": {"id": CID}}]
        }))
        for folder, enabled, seed in ((walk_state_name, include_walk, 100),
                                      ("Idle", include_idle, 180)):
            if not enabled:
                continue
            for direction in DIRECTIONS:
                for frame in range(8):
                    if (folder, direction, frame) == missing:
                        continue
                    color = (seed + frame, 50, 80, 255)
                    image = Image.new("RGBA", (88, 88), color)
                    buffer = io.BytesIO()
                    image.save(buffer, "PNG")
                    archive.writestr(
                        f"{folder}/animations/walking/{direction}/frame_{frame:03}.png",
                        buffer.getvalue()
                    )
    return root, target


class WalkFromCorrectStateTests(unittest.TestCase):
    def test_selects_walk_even_if_idle_walking_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root, exported = make_export(Path(directory))
            result = replace_walk(exported, root, fingerprint=IDENTITY)
            self.assertEqual(result["status"], "updated")
            self.assertEqual(result["sourceState"], "walk")
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertEqual(manifest["motions"]["walk"]["sourceState"], "walk")
            self.assertEqual(manifest["motions"]["walk"]["frames"], 8)
            with Image.open(root / "walk.png") as atlas:
                self.assertEqual(atlas.size, (704, 704))
                self.assertEqual(atlas.getpixel((7 * 88 + 5, 7 * 88 + 5)),
                                 (107, 50, 80, 255))
            self.assertEqual(replace_walk(exported, root, fingerprint=IDENTITY)["status"],
                             "unchanged")

    def test_missing_new_state_preserves_old_not_idle(self):
        with tempfile.TemporaryDirectory() as directory:
            root, exported = make_export(Path(directory), include_walk=False)
            old = (root / "walk.png").read_bytes()
            result = replace_walk(exported, root, fingerprint=IDENTITY)
            self.assertEqual(result["status"], "selected_state_missing")
            self.assertEqual((root / "walk.png").read_bytes(), old)

    def test_partial_new_state_preserves_old(self):
        with tempfile.TemporaryDirectory() as directory:
            root, exported = make_export(Path(directory),
                                        missing=("walk", "west", 7))
            result = replace_walk(exported, root, fingerprint=IDENTITY)
            self.assertEqual(result["status"], "incomplete_selected_walk")

    def test_case_insensitive_state_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root, exported = make_export(Path(directory), walk_state_name="Walk")
            self.assertEqual(replace_walk(exported, root, fingerprint=IDENTITY)["status"],
                             "updated")

    def test_rejects_wrong_character(self):
        with tempfile.TemporaryDirectory() as directory:
            root, exported = make_export(Path(directory))
            with self.assertRaises(ValueError):
                replace_walk(exported, root, fingerprint="0" * 64)


if __name__ == "__main__":
    unittest.main()
