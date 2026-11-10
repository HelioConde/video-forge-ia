"""Testes offline de importação segura e incremental dos movimentos do Alex."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

try:
    from PIL import Image
except ImportError:
    Image = None
from scripts.import_pixellab_production import produce_atlases, FINGERPRINT

# Hash não é reversível; para testes, substituir a constante por um fingerprint de teste.
TEST_ID = "identity-example-not-private"
MOTIONS = [
    {"motion":"talk_explain","directions":["south","north"],"kind":"character","category":"conversa"},
    {"motion":"sip_coffee","directions":["south"],"kind":"character","category":"cafe"},
]


def make_export(path, completed, *, bad=False):
    with ZipFile(path,"w") as bundle:
        bundle.writestr("metadata.json",json.dumps({
            "states":[{"character":{"id":TEST_ID}}]
        }))
        for motion in completed:
            item=next(x for x in MOTIONS if x["motion"]==motion)
            for d in item["directions"]:
                for frame in range(4):
                    img=Image.new("RGBA",(88,88),(120,62+frame,42,255))
                    if bad and frame==3:
                        img=Image.new("RGBA",(88,88),(0,0,0,0))
                    out=io.BytesIO();img.save(out,"PNG")
                    bundle.writestr(
                        f"Idle/animations/{motion}/{d}/frame_{frame:03}.png",out.getvalue()
                    )


@unittest.skipUnless(Image is not None,"Pillow não instalado")
class ReceiveTests(unittest.TestCase):
    def test_partial_then_incremental_completion_preserves_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);zip_file=folder/"export.zip";assets=folder/"assets"
            with patch("scripts.import_pixellab_production.read_catalog",return_value=MOTIONS), \
                 patch("scripts.import_pixellab_production.FINGERPRINT",hashlib.sha256(TEST_ID.encode()).hexdigest()):
                make_export(zip_file,["talk_explain"])
                one=produce_atlases(zip_file,assets)
                self.assertEqual(one["status"],"partial")
                self.assertEqual(one["availableMotionCount"],1)
                original=(assets/"talk_explain.png").read_bytes()
                make_export(zip_file,["sip_coffee"])
                two=produce_atlases(zip_file,assets)
                self.assertEqual(two["status"],"complete")
                self.assertEqual(two["availableMotionCount"],2)
                self.assertEqual((assets/"talk_explain.png").read_bytes(),original)
                self.assertEqual(len(two["motions"]),2)
                self.assertTrue((assets/"sip_coffee.png").is_file())
                self.assertNotIn("character_id", (assets/"manifest.json").read_text())
                self.assertNotIn(TEST_ID,(assets/"manifest.json").read_text())
    def test_bad_frame_keeps_old_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);src=folder/"export.zip";dst=folder/"assets"
            with patch("scripts.import_pixellab_production.read_catalog",return_value=MOTIONS), \
                 patch("scripts.import_pixellab_production.FINGERPRINT",hashlib.sha256(TEST_ID.encode()).hexdigest()):
                make_export(src,["talk_explain"])
                produce_atlases(src,dst)
                old=(dst/"manifest.json").read_bytes()
                make_export(src,["sip_coffee"],bad=True)
                with self.assertRaises(ValueError):
                    produce_atlases(src,dst)
                self.assertEqual((dst/"manifest.json").read_bytes(),old)
    def test_strict_rejects_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);src=folder/"export.zip";dst=folder/"assets"
            with patch("scripts.import_pixellab_production.read_catalog",return_value=MOTIONS), \
                 patch("scripts.import_pixellab_production.FINGERPRINT",hashlib.sha256(TEST_ID.encode()).hexdigest()):
                make_export(src,["talk_explain"])
                with self.assertRaises(ValueError):
                    produce_atlases(src,dst,require_all=True)
                self.assertFalse(dst.exists())


if __name__=="__main__":
    unittest.main()
