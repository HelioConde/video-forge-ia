import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from PIL import Image
from scripts.refresh_pixellab_walk import replace_walk, DIRECTIONS

CID="test-pixellab"
HASH=hashlib.sha256(CID.encode()).hexdigest()

def fixture(folder, name="walk_v2", incomplete=False):
    root=folder/"alex";root.mkdir()
    old=Image.new("RGBA",(352,704),(44,66,88,255))
    buffer=io.BytesIO();old.save(buffer,"PNG",optimize=True);data=buffer.getvalue()
    (root/"walk.png").write_bytes(data)
    (root/"manifest.json").write_text(json.dumps({
        "schema":"videoforge/pixellab-agent-atlas/v1","character":"alex",
        "frameWidth":88,"frameHeight":88,"frames":4,"directions":list(DIRECTIONS),
        "motions":{"walk":{"file":"walk.png","sha256":hashlib.sha256(data).hexdigest(),
                           "width":352,"height":704}}
    }))
    zip_path=folder/"export.zip"
    with ZipFile(zip_path,"w") as z:
        z.writestr("metadata.json",json.dumps({"states":[{"character":{"id":CID}}]}))
        for d in DIRECTIONS:
            for n in range(4):
                if incomplete and d=="west" and n==3:continue
                img=Image.new("RGBA",(88,88),(100+n,40,30,255))
                b=io.BytesIO();img.save(b,"PNG")
                z.writestr(f"Idle/animations/{name}/{d}/frame_{n:03}.png",b.getvalue())
    return root,zip_path

class RefreshWalkTests(unittest.TestCase):
    def test_valid_new_walk_replaces_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,export=fixture(Path(tmp))
            old=(root/"walk.png").read_bytes()
            result=replace_walk(export,root,fingerprint=HASH)
            self.assertEqual(result["status"],"updated")
            self.assertEqual(result["source"],"walk_v2")
            self.assertNotEqual((root/"walk.png").read_bytes(),old)
            self.assertEqual(replace_walk(export,root,fingerprint=HASH)["status"],"unchanged")
    def test_incomplete_does_not_touch_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,export=fixture(Path(tmp),incomplete=True)
            before=(root/"walk.png").read_bytes()
            self.assertEqual(replace_walk(export,root,fingerprint=HASH)["status"],"incomplete")
            self.assertEqual((root/"walk.png").read_bytes(),before)
    def test_bad_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,export=fixture(Path(tmp))
            with self.assertRaises(ValueError):
                replace_walk(export,root,fingerprint="0"*64)
    def test_replaced_same_name_walk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,export=fixture(Path(tmp),name="walk")
            self.assertEqual(replace_walk(export,root,fingerprint=HASH)["source"],"walk")

if __name__=="__main__":unittest.main()
