"""Valida recepção somente GET de múltiplas imagens por objeto."""
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
    Image=None

from scripts.import_pixellab_objects import receive_objects, parse_spritesheet
from videoforge.pixellab.production_object_build import CHAIR, CABINET

CHAIR_ID="123e4567-e89b-12d3-a456-426614174002"
CABINET_ID="123e4567-e89b-12d3-a456-426614174003"


def zip_pngs():
    data=io.BytesIO()
    with ZipFile(data,"w") as archive:
        for i in range(2):
            image=Image.new("RGBA",(96,96),(100+i,100,110,255))
            png=io.BytesIO();image.save(png,"PNG")
            archive.writestr("animated/sprite-"+str(i)+".png",png.getvalue())
        archive.writestr("layout.json",json.dumps({"private_reference":"do-not-publish"}))
    return data.getvalue()


class Fake:
    def _request(self, method, path, *, query=None):
        if method=="GET" and path=="/objects":
            items=[{"id":CHAIR_ID,"name":CHAIR,"status":"completed"},
                   {"id":CABINET_ID,"name":CABINET,"status":"completed"}]
            return {"objects":items,"total":len(items)}
        if path in ("/objects/"+CHAIR_ID,"/objects/"+CABINET_ID):
            return {"preview_url":None,"animations":[]}
        raise AssertionError("GET desconhecido: "+path)
    def download_object_spritesheet(self,oid):
        return zip_pngs()


@unittest.skipUnless(Image is not None,"Pillow não instalado")
class ObjectReceiveTests(unittest.TestCase):
    def test_accepts_every_png_without_exposing_private_layout(self):
        sprites=parse_spritesheet(zip_pngs())
        self.assertEqual(len(sprites),2)
        self.assertEqual([x[0] for x in sprites],["sprite-000.png","sprite-001.png"])
    def test_receives_two_objects_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"site"
            r=receive_objects(Fake(),output)
            self.assertEqual(r["status"],"complete")
            self.assertEqual(r["received"],2)
            manifest=json.loads((output/"manifest.json").read_text())
            self.assertEqual(manifest["availableObjectCount"],2)
            self.assertEqual(len(manifest["objects"]["cabinet"]["files"]),2)
            content=json.dumps(manifest)
            for secret in (CHAIR_ID,CABINET_ID,"private_reference","preview_url"):
                self.assertNotIn(secret,content)
            self.assertTrue((output/"cabinet/sprite-000.png").exists())
            self.assertTrue((output/"office-chair/sprite-001.png").exists())
    def test_preserves_existing_if_export_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"site"
            with patch("scripts.import_pixellab_objects._download_preview",return_value=False):
                receive_objects(Fake(),output)
                class Missing(Fake):
                    def download_object_spritesheet(self,oid):
                        raise ValueError("offline")
                r=receive_objects(Missing(),output)
            self.assertEqual(r["received"],2)
            self.assertEqual(r["status"],"complete")
            self.assertEqual(len(json.loads((output/"manifest.json").read_text())["objects"]),2)


if __name__=="__main__":
    unittest.main()
