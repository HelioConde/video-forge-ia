"""Walk PixMinimax: preserva 8 quadros e nunca regride ao atlas de 4."""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from PIL import Image
from scripts.refresh_pixellab_walk import replace_walk, DIRECTIONS

TEST_ID="video-forge-test-character"
FINGERPRINT=hashlib.sha256(TEST_ID.encode()).hexdigest()

def make_export(root: Path, *, name="walking", count=8, omit=None, old_frames=4):
    atlas_dir=root/"alex";atlas_dir.mkdir()
    orig=Image.new("RGBA",(88*old_frames,704),(50,50,50,255))
    buf=io.BytesIO();orig.save(buf,"PNG")
    old=buf.getvalue()
    (atlas_dir/"walk.png").write_bytes(old)
    (atlas_dir/"manifest.json").write_text(json.dumps({
        "schema":"videoforge/pixellab-agent-atlas/v1",
        "character":"alex","frames":4,"frameWidth":88,"frameHeight":88,
        "directions":list(DIRECTIONS),
        "motions":{"walk":{"file":"walk.png","width":88*old_frames,
                           "height":704,"frames":old_frames,
                           "sha256":hashlib.sha256(old).hexdigest()}}
    }))
    export=root/"export.zip"
    with ZipFile(export,"w") as zipout:
        zipout.writestr("metadata.json",json.dumps({"states":[{"character":{"id":TEST_ID}}]}))
        for direction in DIRECTIONS:
            for frame in range(count):
                if (direction,frame)==omit: continue
                tile=Image.new("RGBA",(88,88),(100+frame,55,75,255))
                tmp=io.BytesIO();tile.save(tmp,"PNG")
                zipout.writestr(
                    f"Idle/animations/{name}/{direction}/frame_{frame:03}.png",
                    tmp.getvalue())
    return atlas_dir, export

class WalkTests(unittest.TestCase):
    def test_walking_full_eight_frames_kept_and_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root,zipfile=make_export(Path(d))
            result=replace_walk(zipfile,root,fingerprint=FINGERPRINT)
            self.assertEqual(result["status"],"updated")
            self.assertEqual(result["source"],"walking")
            manifest=json.loads((root/"manifest.json").read_text())
            self.assertEqual(manifest["motions"]["walk"]["frames"],8)
            self.assertEqual(manifest["motions"]["walk"]["width"],704)
            with Image.open(root/"walk.png") as atlas:
                self.assertEqual(atlas.size,(704,704))
                self.assertEqual(atlas.getpixel((7*88+5,7*88+5)),(107,55,75,255))
            self.assertEqual(replace_walk(zipfile,root,fingerprint=FINGERPRINT)["status"],"unchanged")

    def test_incomplete_eight_frame_export_does_not_replace_walk(self):
        with tempfile.TemporaryDirectory() as d:
            root,z=make_export(Path(d),omit=("west",7))
            previous=(root/"walk.png").read_bytes()
            result=replace_walk(z,root,fingerprint=FINGERPRINT)
            self.assertEqual(result["status"],"incomplete")
            self.assertEqual(previous,(root/"walk.png").read_bytes())

    def test_walking_with_only_four_frames_is_incomplete(self):
        with tempfile.TemporaryDirectory() as d:
            root,z=make_export(Path(d),count=4)
            self.assertEqual(replace_walk(z,root,fingerprint=FINGERPRINT)["status"],"incomplete")

    def test_wrong_character_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root,z=make_export(Path(d))
            with self.assertRaises(ValueError):
                replace_walk(z,root,fingerprint="0"*64)

    def test_can_accept_legacy_four_frame_walk_without_downgrading_eight(self):
        with tempfile.TemporaryDirectory() as d:
            root,z=make_export(Path(d),name="walk",count=4)
            self.assertEqual(replace_walk(z,root,fingerprint=FINGERPRINT)["status"],"updated")
        with tempfile.TemporaryDirectory() as d:
            root,z=make_export(Path(d),name="walk",count=4,old_frames=8)
            self.assertEqual(replace_walk(z,root,fingerprint=FINGERPRINT)["status"],"no_new_walk")

if __name__=="__main__":
    unittest.main()
