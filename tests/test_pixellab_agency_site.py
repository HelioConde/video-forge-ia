"""A sede única PixelLab precisa ser asset real, não uma imagem simulada."""
import hashlib
import struct
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCENE=ROOT/"site/assets/pixellab/scenes/agencia-unificada.png"
SHA256="c975d4c04c2ac885efc9e12ad5158afe413bf79ca29819e03fa071ac8c107c54"


class PixelLabAgencyIntegrationTest(unittest.TestCase):
    def test_real_image_from_approved_workflow_is_versioned(self):
        raw=SCENE.read_bytes()
        self.assertEqual(raw[:8],b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II",raw[16:24]),(688,384))
        self.assertEqual(hashlib.sha256(raw).hexdigest(),SHA256)
        self.assertGreater(len(raw),40_000)

    def test_office_background_loads_agency_as_primary_scene(self):
        src=(ROOT/"site/office-art.js").read_text(encoding="utf-8")
        self.assertIn("agency:'scenes/agencia-unificada.png'",src)
        self.assertIn("if(spriteImages.agency){pixelAgency(c);return;}",src)
        self.assertIn("c.imageSmoothingEnabled=false",src)
        self.assertIn("window.VideoForgeOfficeMap.scene",src)
        self.assertIn("c.drawImage(image,src.x,src.y,src.w,src.h,dst.x,dst.y,dst.w,dst.h)",src)
        self.assertNotIn("sprite(c,'main',79,194,512,512)",src)
        self.assertIn("paintAgents:",src)

    def test_routes_and_map_remain_integrated(self):
        routing=(ROOT/"site/agent-routines.js").read_text(encoding="utf-8")
        layout=(ROOT/"site/office-map.js").read_text(encoding="utf-8")
        self.assertIn("navigation=Object.freeze",layout)
        self.assertIn("hallY:454",layout)
        self.assertIn("window.VideoForgeOfficeMap?.navigation",routing)
        self.assertIn('production:{',layout)
        self.assertIn("meetings=Object.freeze",layout)


if __name__=="__main__":
    unittest.main()
