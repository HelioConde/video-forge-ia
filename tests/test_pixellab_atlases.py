"""Valida assets públicos e manifesto de animação do Alex sem PixelLab/API."""
import hashlib
import json
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "site/assets/pixellab/agents/alex"
DIRECTIONS = ["south", "south-east", "east", "north-east",
              "north", "north-west", "west", "south-west"]
MOTIONS = ["idle", "walk", "type", "sit", "talk", "wave"]


class PublicAtlasTests(unittest.TestCase):
    def test_manifest_structure_and_48_combinations(self):
        manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "videoforge/pixellab-agent-atlas/v1")
        self.assertEqual(manifest["character"], "alex")
        self.assertEqual(manifest["directions"], DIRECTIONS)
        self.assertEqual((manifest["frameWidth"], manifest["frameHeight"]), (88, 88))
        self.assertEqual(manifest["frames"], 4)
        self.assertEqual(set(manifest["motions"]), set(MOTIONS))
        self.assertEqual(len(manifest["motions"]) * len(DIRECTIONS), 48)
        raw = (ASSETS / "manifest.json").read_text(encoding="utf-8").lower()
        self.assertNotIn("character_id", raw)
        self.assertNotIn("token", raw)
        self.assertNotIn("prompt", raw)

    def test_atlas_files_are_complete_and_match_sha256(self):
        manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
        for motion in MOTIONS:
            with self.subTest(motion=motion):
                details = manifest["motions"][motion]
                self.assertEqual(details["file"], motion + ".png")
                data = (ASSETS / details["file"]).read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                dimensions = struct.unpack(">II", data[16:24])
                self.assertEqual(dimensions, (352, 704))
                self.assertEqual((details["width"], details["height"]), dimensions)
                self.assertEqual(data[25], 6)  # PNG RGBA
                self.assertEqual(hashlib.sha256(data).hexdigest(), details["sha256"])

    def test_site_loads_animator_before_canvas(self):
        html = (ROOT / "site/index.html").read_text(encoding="utf-8")
        self.assertLess(html.index('src="./agent-animator.js"'),
                        html.index('src="./office-art.js"'))
        self.assertLess(html.index('src="./office-art.js"'),
                        html.index('src="./office-renderer.js"'))
        js = (ROOT / "site/office-renderer.js").read_text(encoding="utf-8")
        self.assertIn("this.previewMotion", js)
        self.assertIn("this.reduceMotion", js)


if __name__ == "__main__":
    unittest.main()
