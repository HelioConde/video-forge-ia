"""Only mocked image requests; zero actual Proxy/image generation calls or costs."""
from __future__ import annotations

import base64
import copy
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from videoforge.generators.autoeditor import (
    AutoEditorBlocked, generate_images, load_manifest, validate_manifest,
)
from videoforge.production.visual_lock import (
    VisualLockError, resolve_reference_image, scene_prompt,
    validate_visual_lock, verify_anchor_trace,
)
from videoforge.proxy.client import ProxyError

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "geradores/autoeditor/exemplo-manifesto.json"


def png_bytes(idx: int) -> bytes:
    im = Image.new("RGB", (720, 1280), (30 + idx, 35, 60 + idx))
    draw = ImageDraw.Draw(im)
    for n in range(25):
        draw.rectangle((n * 13, n * 27, 300 + idx + n, 600 + n),
                       outline=(150 + idx, 80 + n, 30 + idx), width=3)
    file = io.BytesIO()
    im.save(file, format="PNG")
    assert len(file.getvalue()) > 1000
    return file.getvalue()


class MockArtist:
    def __init__(self, fail_edit=False):
        self.requests = []
        self.fail_edit = fail_edit

    def _response(self, n):
        return {"data": [{"b64_json": base64.b64encode(png_bytes(n)).decode()}]}

    def images_generate(self, body):
        self.requests.append(("generate", body))
        return self._response(1)

    def images_edit_files(self, **kwargs):
        if self.fail_edit:
            self.requests.append(("edit_error", kwargs))
            raise ProxyError("Codex Proxy HTTP 429")
        if "images" not in kwargs or len(kwargs["images"]) != 1:
            raise AssertionError("Image anchor required on every edit")
        path = Path(kwargs["images"][0])
        if not path.is_file():
            raise AssertionError("Missing anchor bytes")
        self.requests.append(("edit", {
            "prompt": kwargs["prompt"],
            "model": kwargs["model"],
            "path": str(path),
            "ref_hash": sha256(path.read_bytes()).hexdigest(),
        }))
        return self._response(len(self.requests))


class VisualLockTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest(MANIFEST)

    def test_eight_scenes_use_one_generated_anchor_and_seven_reference_edits(self):
        mock = MockArtist()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            assets = generate_images(self.manifest, output, mock, max_calls=8)
            self.assertEqual(len(mock.requests), 8)
            self.assertEqual([t for t, _ in mock.requests],
                             ["generate"] + ["edit"] * 7)
            self.assertEqual(assets[0]["generation_mode"], "canonical_anchor")
            self.assertEqual(assets[1]["generation_mode"], "reference_image_edit")
            anchor = assets[0]["output_sha256"]
            for stage, request in mock.requests[1:]:
                self.assertEqual(stage, "edit")
                self.assertEqual(request["ref_hash"], anchor)
                self.assertEqual(request["path"], str(output / "scene-1.png"))
                self.assertIn("ART-DIRECTION", request["prompt"])
                self.assertIn("SAME", request["prompt"].upper())
            audit = json.loads((output/"imagens.json").read_text())["visual_audit"]
            self.assertEqual(audit["reference_image_edits_verified"], 7)
            self.assertTrue(audit["anchor_reference_provenance_verified"])
            self.assertFalse(audit["actual_visual_identity_verified"])
            self.assertFalse(audit["youtube_upload_approved"])

    def test_429_on_edit_aborts_after_one_anchor_and_does_not_fallback(self):
        mock = MockArtist(fail_edit=True)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(AutoEditorBlocked, "HTTP 429"):
                generate_images(self.manifest, Path(tmp), mock, max_calls=8)
            self.assertEqual([x[0] for x in mock.requests],
                             ["generate", "edit_error"])
            self.assertFalse((Path(tmp) / "imagens.json").exists())

    def test_reference_can_be_supplied_only_from_same_channels_asset_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "canal" / "otaku-br" / "referencias" / "protagonista.png"
            reference.parent.mkdir(parents=True)
            reference.write_bytes(png_bytes(4))
            bible = dict(self.manifest["visual_lock"],
                         reference_path="canal/otaku-br/referencias/protagonista.png")
            checked = validate_visual_lock(bible)
            self.assertEqual(resolve_reference_image(checked, channel="otaku-br", root=root), reference)
            with self.assertRaisesRegex(VisualLockError, "OUTSIDE_CHANNEL"):
                resolve_reference_image(checked, channel="gamer", root=root)
            with self.assertRaisesRegex(VisualLockError, "PATH_INVALID"):
                validate_visual_lock(dict(bible, reference_path="../../private.png"))

    def test_provided_reference_uses_edit_for_first_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "canal/otaku-br/referencias/visual.png"
            reference.parent.mkdir(parents=True)
            reference.write_bytes(png_bytes(12))
            manifest = copy.deepcopy(self.manifest)
            manifest["visual_lock"]["reference_path"] = "canal/otaku-br/referencias/visual.png"
            mock = MockArtist()
            with patch("videoforge.generators.autoeditor.ROOT", root):
                # Media validation policy is still read from the registered project ROOT.
                assets = generate_images(manifest, root, mock, max_calls=8)
            self.assertTrue(all(entry[0] == "edit" for entry in mock.requests))
            self.assertEqual(mock.requests[0][1]["path"], str(reference))
            self.assertEqual(assets[0]["generation_mode"], "reference_image_edit")
            self.assertTrue(assets[0]["source_reference_sha256"])
            self.assertTrue(verify_anchor_trace(assets, manifest["visual_lock"])["anchor_reference_provenance_verified"])

    def test_missing_bible_or_style_conflict_stops_before_paid_calls(self):
        for bad in [
            dict(self.manifest, visual_lock=None),
            dict(self.manifest, visual_lock=dict(self.manifest["visual_lock"], style_family="unknown")),
            dict(self.manifest, visual_lock=dict(self.manifest["visual_lock"],
                 render_style="photographic live-action image")),
        ]:
            with self.subTest(bad=bool(bad)):
                with self.assertRaises(VisualLockError):
                    validate_manifest(bad)
        scene = dict(self.manifest["cenas"][1],
                     prompt_imagem="photorealistic live-action portrait")
        with self.assertRaisesRegex(VisualLockError, "CONTRADICTS_VISUAL_BIBLE"):
            scene_prompt(scene, self.manifest["visual_lock"], first=False)

    def test_forged_unanchored_scene_is_rejected(self):
        mock = MockArtist()
        with tempfile.TemporaryDirectory() as tmp:
            assets = generate_images(self.manifest, Path(tmp), mock, max_calls=8)
            altered = copy.deepcopy(assets)
            altered[3]["anchor_sha256"] = "0" * 64
            with self.assertRaisesRegex(VisualLockError, "NOT_ANCHORED"):
                verify_anchor_trace(altered, self.manifest["visual_lock"])


if __name__ == "__main__":
    unittest.main()
