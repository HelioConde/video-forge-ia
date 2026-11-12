"""Offline tests of real VideoForge layer contracts: mock Proxy, no AI spend."""
from __future__ import annotations

import base64
import copy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from videoforge.generators import load_generator, build_generator_plan
from videoforge.generators.autoeditor import (
    AutoEditorBlocked, build_remotion_props, generate_images,
    load_manifest, plan, produce, validate_manifest,
)
from videoforge.production.scene_layers import (
    SceneLayerError, count_image_requests, generate_scene_layers,
    validate_layer_plan, verify_scene_layers,
)
from videoforge.proxy.client import ProxyError

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "geradores/autoeditor/exemplo-manifesto.json"


def _png(n: int, *, transparent: bool = False, pretend_alpha: bool = False) -> bytes:
    mode = "RGBA" if transparent and not pretend_alpha else "RGB"
    image = Image.new(mode, (720, 1280),
                      (0, 0, 0, 0) if mode == "RGBA" else (21 + n, 42, 61))
    art = ImageDraw.Draw(image)
    if mode == "RGBA":
        art.ellipse((130, 180, 550, 990), fill=(121, 72 + n, 36, 255))
        art.rectangle((210, 750, 520, 1060), fill=(39, 72, 116, 255))
    else:
        for i in range(18):
            art.line((i*28, 34, 700-i*19, 1050), fill=(70+n, 112+i, 137), width=8)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    assert len(buf.getvalue()) > 1000
    return buf.getvalue()


class MockVideoForgeArtist:
    def __init__(self, *, fail_layer=False, opaque_cutout=False):
        self.calls = []
        self.fail_layer = fail_layer
        self.opaque_cutout = opaque_cutout

    def _response(self, body: bytes):
        return {"data": [{"b64_json": base64.b64encode(body).decode()}]}

    def images_generate(self, body):
        self.calls.append({"role": "master", "reference": None})
        return self._response(_png(len(self.calls)))

    def images_edit_files(self, *, prompt, images, model, n=1, **options):
        assert n == 1
        assert len(images) == 1
        ref = Path(images[0])
        assert ref.is_file()
        if "EDIT THE ACTUAL ATTACHED MASTER SCENE" not in prompt:
            role = "master_followup"
        elif options.get("background") == "transparent":
            role = "cutout"
        else:
            role = "background"
        self.calls.append({
            "role": role,
            "reference": ref,
            "reference_hash": sha256(ref.read_bytes()).hexdigest(),
            "transparent_setting": options.get("background"),
            "prompt": prompt,
        })
        if self.fail_layer and role == "background":
            raise ProxyError("API exhausted; no retries allowed")
        if role == "cutout":
            return self._response(_png(len(self.calls),
                                       transparent=True,
                                       pretend_alpha=self.opaque_cutout))
        return self._response(_png(len(self.calls)))


class NoAccountProxy:
    def __init__(self):
        self.calls = 0
    def accounts(self):
        self.calls += 1
        raise RuntimeError("accounts() must never be called before budget check")


class LayerPipelineTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest(MANIFEST)

    def _create(self, directory: Path, artist=None, manifest=None):
        artist = artist or MockVideoForgeArtist()
        manifest = manifest or self.manifest
        budget = count_image_requests(manifest)
        masters = generate_images(manifest, directory, artist, max_calls=budget)
        doc = generate_scene_layers(manifest, directory, artist,
                                    master_assets=masters, max_calls=budget)
        return artist, masters, doc

    def test_every_agent_has_correct_dag_role_and_approval_dependency(self):
        definition = load_generator("autoeditor")
        graph = build_generator_plan(definition)
        tasks = {x["id"]: x for x in graph["tasks"]}
        assigned = {
            "storyboard": "storyboard",
            "imagens": "ilustrador",
            "decomposicao": "ilustrador",
            "qa-camadas": "revisor-visual",
            "qa-imagens": "revisor-visual",
            "animacao": "animacao",
            "edicao": "montagem",
            "qa-tecnico": "qa-tecnico",
            "qa-editorial": "revisor-conteudo",
        }
        for stage, worker in assigned.items():
            with self.subTest(stage=stage):
                self.assertEqual(tasks[stage]["responsavel"], worker)
                self.assertEqual(tasks[stage]["execution_status"], "not_started")
        self.assertEqual(tasks["decomposicao"]["depende_de"], ["imagens"])
        self.assertEqual(tasks["qa-camadas"]["depende_de"], ["decomposicao"])
        self.assertEqual(tasks["qa-imagens"]["depende_de"], ["qa-camadas"])
        self.assertEqual(tasks["animacao"]["depende_de"], ["qa-imagens", "legendas"])
        self.assertEqual(tasks["edicao"]["depende_de"], ["animacao"])
        self.assertEqual(tasks["qa-tecnico"]["depende_de"], ["edicao"])
        self.assertNotIn("publicacao", tasks)
        self.assertFalse(graph["execution_enabled"])
        self.assertFalse(graph["auto_publish_enabled"])
        self.assertTrue(graph["requires_human_approval"])

    def test_budget_counts_all_background_character_and_prop_edits(self):
        p = plan(self.manifest)
        self.assertEqual(p["planned_master_scenes"], 8)
        self.assertEqual(p["planned_layer_image_calls"], 18)
        self.assertEqual(p["planned_image_calls"], 26)
        self.assertEqual(p["scene_decomposition_mode"], "layered_from_master_scene")
        self.assertFalse(p["execution_enabled"])
        self.assertFalse(p["youtube_uploaded"])

    def test_true_per_scene_master_reference_and_separate_character_prop_pngs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            proxy, masters, output = self._create(root)
            self.assertEqual(len(proxy.calls), 26)
            self.assertEqual([x["role"] for x in proxy.calls[:8]],
                             ["master"] + ["master_followup"]*7)
            self.assertEqual(output["master_image_requests"], 8)
            self.assertEqual(output["image_requests"], 18)
            for idx, row in enumerate(output["scenes"], 1):
                master = root / f"scene-{idx}.png"
                # Original full scene is retained; cutouts never replace it.
                self.assertEqual(row["master_sha256"], sha256(master.read_bytes()).hexdigest())
                self.assertEqual(row["background"]["file"],
                                 f"scene-{idx}/background.png")
                self.assertEqual(len(row["characters"]), 1)
                self.assertEqual(row["characters"][0]["source_master_sha256"],
                                 row["master_sha256"])
                char = root / row["characters"][0]["file"]
                with Image.open(char) as image:
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(image.size, (720,1280))
                    self.assertEqual(image.getchannel("A").getextrema(), (0,255))
            self.assertEqual(len(output["scenes"][1]["movable_props"]), 1)
            self.assertEqual(len(output["scenes"][5]["movable_props"]), 1)
            # Every layer edit references the master of its own scene,
            # not a new hallucinated image or the global character anchor.
            expected = [row["master_sha256"] for row in output["scenes"]]
            for idx, row in enumerate(output["scenes"], 1):
                matching = [x for x in proxy.calls if x["role"] in ("background","cutout")
                            and x["reference"] == root/f"scene-{idx}.png"]
                self.assertEqual(len(matching), 3 if idx in (2,6) else 2)
                self.assertTrue(all(x["reference_hash"]==expected[idx-1]
                                    for x in matching))
            qa = verify_scene_layers(self.manifest, root, output)
            self.assertTrue(qa["true_png_transparency_verified"])
            self.assertTrue(qa["image_origin_and_hash_verified"])
            self.assertFalse(qa["subject_alignment_verified"])
            self.assertFalse(qa["approved_for_youtube"])
            self.assertFalse((root/"qa-camadas.json").exists(),
                             "QA must be authored by the Revisor stage, not the artist")

    def test_remotion_uses_real_background_and_rgba_layers_not_duplicate_full_scene(self):
        with tempfile.TemporaryDirectory() as d:
            artist, masters, document = self._create(Path(d))
            source = " ".join(s["narracao"] for s in self.manifest["cenas"])
            words = [{"start": .3+i*.36, "end": .5+i*.36, "text":word}
                     for i,word in enumerate(source.split())]
            props = build_remotion_props(self.manifest, 110., words,
                                        staging_id="vf-autoeditor-test",
                                        layer_document=document)
            scenes=props["scenes"]
            self.assertEqual(len(scenes),8)
            self.assertTrue(all(s["renderMode"]=="multilayer" for s in scenes))
            self.assertEqual(scenes[0]["background"],
                             "generated/vf-autoeditor-test/scene-1/background.png")
            self.assertNotEqual(scenes[0]["background"],
                                "generated/vf-autoeditor-test/scene-1.png")
            self.assertEqual(scenes[0]["layers"][0]["role"],"front_character")
            self.assertEqual(scenes[1]["layers"][1]["role"],"hero_prop")
            self.assertEqual(scenes[1]["layers"][0]["heroRisk"],.08)
            self.assertIn("scene-2/movable_props/caderno.png",
                          scenes[1]["layers"][1]["src"])
            self.assertEqual(props["durationFrames"],3300)

    def test_no_characters_means_master_background_and_no_wasted_edit(self):
        manifest=copy.deepcopy(self.manifest)
        manifest["cenas"][0]["layer_plan"]={"characters":[],"movable_props":[]}
        with tempfile.TemporaryDirectory() as d:
            _,_,doc=self._create(Path(d),manifest=manifest)
            self.assertEqual(doc["image_requests"],16)
            self.assertEqual(doc["scenes"][0]["background"]["file"],"scene-1.png")
            self.assertEqual(doc["scenes"][0]["characters"],[])

    def test_fail_closed_if_cutout_is_opaque_or_api_fails(self):
        for proxy, expected in [
            (MockVideoForgeArtist(opaque_cutout=True), "ALPHA_CHANNEL_MISSING"),
            (MockVideoForgeArtist(fail_layer=True), "BACKGROUND_EDIT_FAILED"),
        ]:
            with tempfile.TemporaryDirectory() as d:
                directory=Path(d)
                masters=generate_images(self.manifest,directory,proxy,max_calls=26)
                with self.assertRaisesRegex(SceneLayerError, expected):
                    generate_scene_layers(self.manifest,directory,proxy,
                                          master_assets=masters,max_calls=26)
                self.assertFalse((directory/"scene-layers.json").exists())
                self.assertFalse((directory/"qa-camadas.json").exists())

    def test_budget_refusal_before_proxy_accounts_or_expense(self):
        proxy=NoAccountProxy()
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ,{"VIDEOFORGE_AUTOEDITOR_RENDER_AUTHORIZED":"yes"}):
                with self.assertRaisesRegex(AutoEditorBlocked, "IMAGE_BUDGET_INVALID"):
                    produce(self.manifest, destination=Path(d)/"render",
                            motion_root=Path(d),job_id="expensive-test",
                            max_calls=12,proxy=proxy)
        self.assertEqual(proxy.calls,0)

    def test_storyboard_has_valid_identifiers_unique_movable_props_and_reviewer(self):
        invalid=[
            {"characters": [{"id":"../private","description":"unsafe character"}],"movable_props":[]},
            {"characters": [{"id":"person","description":"person one"}],
             "movable_props": [{"id":"person","description":"duplicated person"}]},
            {"characters":[],"movable_props":[{"id":"cup","description":"tiny"}]},
            {"characters":[],"movable_props":[],"unknown":"bypass"},
        ]
        for obj in invalid:
            with self.subTest(obj=obj), self.assertRaises(SceneLayerError):
                validate_layer_plan(obj)
        raw=copy.deepcopy(self.manifest)
        raw.pop("scene_decomposition")
        with self.assertRaisesRegex(SceneLayerError,"DECOMPOSITION_REQUIRED"):
            validate_manifest(raw)
        raw=copy.deepcopy(self.manifest)
        raw["scene_decomposition"]["require_independent_visual_review"]=False
        with self.assertRaisesRegex(SceneLayerError, "INDEPENDENT_REVIEW_REQUIRED"):
            validate_manifest(raw)

    def test_qa_detects_tampered_png_after_generation(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            _,_,doc=self._create(directory)
            path=directory/doc["scenes"][0]["characters"][0]["file"]
            path.write_bytes(_png(3,transparent=False))
            with self.assertRaisesRegex(SceneLayerError,"PROVENANCE_MISMATCH"):
                verify_scene_layers(self.manifest,directory,doc)


if __name__=="__main__":
    unittest.main()
