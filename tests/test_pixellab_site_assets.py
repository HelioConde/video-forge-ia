"""Garante que sprites PixelLab publicados são íntegros e acessíveis pelo Canvas."""
import hashlib
import json
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "site"
ASSETS = ROOT / "assets" / "pixellab"
NAMES = {
    "scenes/main-office.png": (256,256),
    "scenes/creative-room.png": (256,256),
    "scenes/media-lab.png": (256,256),
    "objects/desk-pc.png": (96,96),
    "objects/office-chair.png": (64,64),
    "objects/plant.png": (64,64),
    "objects/bookshelf.png": (96,96),
    "objects/audio-mixer.png": (96,96),
    "objects/studio-screen.png": (96,96),
}


class SiteSpritesTests(unittest.TestCase):
    def test_all_nine_original_png_assets_versioned(self):
        manifest=json.loads((ASSETS/"manifest.json").read_text())
        self.assertEqual(manifest["schema"],"videoforge/pixellab-office-assets/v1")
        self.assertEqual(set(manifest["files"]),set(NAMES))
        for name,shape in NAMES.items():
            with self.subTest(sprite=name):
                data=(ASSETS/name).read_bytes()
                self.assertEqual(data[:8],b"\\x89PNG\\r\\n\\x1a\\n")
                self.assertEqual(struct.unpack(">II",data[16:24]),shape)
                self.assertEqual(data[25],6) # RGBA, props transparentes
                self.assertEqual(manifest["files"][name]["sha256"],hashlib.sha256(data).hexdigest())

    def test_sprite_mode_preserves_classic_fallback_and_selection(self):
        art=(ROOT/"office-art.js").read_text()
        renderer=(ROOT/"office-renderer.js").read_text()
        app=(ROOT/"app.js").read_text()
        index=(ROOT/"index.html").read_text()
        for name in NAMES:
            self.assertIn(name,art)
        self.assertIn("pixelBase(c)",art)
        self.assertIn("officeBase(c)",art)
        self.assertIn("setArtMode",art)
        self.assertIn("this.reset()",renderer)
        self.assertIn("agentAt",renderer)
        self.assertIn("btnArtMode",app)
        self.assertIn('id="btnArtMode"',index)
        self.assertIn("imageSmoothingEnabled=false",renderer)
        self.assertNotIn("api.pixellab.ai",art)
        self.assertNotIn("api.pixellab.ai",app)


if __name__ == "__main__":
    unittest.main()
