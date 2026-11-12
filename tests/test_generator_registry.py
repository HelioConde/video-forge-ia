"""Extensibility tests: generator types are data, not a hardcoded whitelist."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from videoforge.config import load_video_config
from videoforge.generators import (
    GeneratorConfigError, build_generator_plan, list_generators,
    load_generator, resolve_generator, validate_definition,
)

ROOT = Path(__file__).resolve().parents[1]


class GeneratorRegistryTests(unittest.TestCase):
    def test_builtin_examples_without_execution(self):
        catalog = list_generators(root=ROOT)
        self.assertEqual({x["id"] for x in catalog}, {"anime", "kids", "dorama", "autoeditor"})
        for item in catalog:
            with self.subTest(generator=item["id"]):
                definition = load_generator(item["id"], root=ROOT)
                plan = build_generator_plan(definition, root=ROOT)
                self.assertEqual(plan["generator_id"], item["id"])
                self.assertEqual(plan["mode"], "plan_only")
                self.assertFalse(plan["execution_enabled"])
                self.assertFalse(plan["auto_publish_enabled"])
                self.assertTrue(plan["requires_human_approval"])
                self.assertEqual(plan["image_source"], "integrated_image_generator_only")
                self.assertEqual(plan["image_failure"], "abort_video")
                self.assertTrue(any(x["operation"] == "image-generation" for x in plan["tasks"]))
                self.assertTrue(all(x["execution_status"] == "not_started" for x in plan["tasks"]))

    def test_channel_selection_and_independent_model(self):
        br = load_video_config("canal/otaku-br/videos/teste-10s/video.json", ROOT) if (
            ROOT / "canal/otaku-br/videos/teste-10s/video.json"
        ).exists() else None
        if br:
            self.assertEqual(br["gerador"]["id"], "anime")
        kids = json.loads((ROOT/"canal/manu-kids/canal.json").read_text(encoding="utf-8"))
        self.assertEqual(resolve_generator(kids, {}, root=ROOT)["id"], "kids")
        anime = json.loads((ROOT/"canal/otaku-br/canal.json").read_text(encoding="utf-8"))
        self.assertEqual(resolve_generator(anime, {}, root=ROOT)["id"], "anime")
        example = load_video_config("canal/alchemy-lab/videos/teste-10s/video.json", ROOT)
        self.assertEqual(example["gerador"]["id"], "dorama")
        self.assertEqual(example["modelo"]["id"], "camadas-animadas")

    def test_video_override_over_channel_and_no_implicit_fallback(self):
        self.assertEqual(resolve_generator(
            {"gerador_padrao": "anime"}, {"gerador": "dorama"}, root=ROOT
        )["id"], "dorama")
        self.assertIsNone(resolve_generator({}, {}, root=ROOT))
        with self.assertRaisesRegex(GeneratorConfigError, "GENERATOR_NOT_REGISTERED"):
            resolve_generator({"gerador_padrao": "anime"}, {"gerador": "inexistente"},
                              root=ROOT)

    def test_open_ended_new_generator_needs_no_python_registration(self):
        # A fourth category can be added by creating a manifest file only.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root/"geradores"/"documentario"
            folder.mkdir(parents=True)
            value = copy.deepcopy(load_generator("anime", root=ROOT))
            value["id"] = "documentario"
            value["nome"] = "Gerador Documentario"
            value["perfil"]["estilo"] = "pesquisa documental ilustrada"
            (folder/"gerador.json").write_text(json.dumps(value), encoding="utf-8")
            self.assertEqual(list_generators(root=root)[0]["id"], "documentario")
            self.assertEqual(resolve_generator({"gerador_padrao": "documentario"}, {},
                                               root=root)["id"], "documentario")

    def test_invalid_ids_cannot_traverse_directories(self):
        for invalid in ("../.secrets", "other/dir", "/tmp", "UPPER", "", "x" * 100):
            with self.subTest(value=invalid):
                with self.assertRaises(GeneratorConfigError):
                    load_generator(invalid, root=ROOT)

    def test_reject_render_before_images_or_missing_generated_visuals(self):
        d = copy.deepcopy(load_generator("anime", root=ROOT))
        image = next(x for x in d["pipeline"] if x["operation"] == "image-generation")
        image.pop("source")
        with self.assertRaisesRegex(GeneratorConfigError, "IMAGE_SOURCE_REQUIRED"):
            validate_definition(d)
        d = copy.deepcopy(load_generator("anime", root=ROOT))
        render = next(x for x in d["pipeline"] if x["operation"] == "render")
        render["after"] = ["voz"]
        with self.assertRaisesRegex(GeneratorConfigError, "RENDER_REQUIRES_ALL_IMAGES"):
            validate_definition(d)

    def test_reject_cyclic_pipeline_and_automatic_publication(self):
        d = copy.deepcopy(load_generator("dorama", root=ROOT))
        d["pipeline"][0]["after"] = ["qa"]
        with self.assertRaisesRegex(GeneratorConfigError, "PIPELINE_CYCLE"):
            validate_definition(d)
        d = copy.deepcopy(load_generator("kids", root=ROOT))
        d["auto_publish_enabled"] = True
        with self.assertRaisesRegex(GeneratorConfigError, "MUST_NOT_AUTOPUBLISH"):
            validate_definition(d)
        d = copy.deepcopy(load_generator("kids", root=ROOT))
        d["execution_enabled"] = True
        with self.assertRaisesRegex(GeneratorConfigError, "CANNOT_ENABLE_EXECUTION"):
            validate_definition(d)


if __name__ == "__main__":
    unittest.main()
