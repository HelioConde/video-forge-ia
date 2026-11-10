import copy
import unittest
from pathlib import Path

from videoforge.config import load_video_config, resolve_model
from videoforge.pipeline import build_storyboard


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = "canal/alchemy-lab/videos/teste-10s/video.json"


class StoryboardTest(unittest.TestCase):
    def setUp(self):
        self.config = load_video_config(EXAMPLE, root=ROOT)

    def test_timeline_for_ten_seconds(self):
        plan = build_storyboard(self.config)
        self.assertEqual(plan["video"]["duration_seconds"], 10)
        self.assertEqual(len(plan["timeline"]), 2)
        self.assertEqual(plan["timeline"][0]["start_seconds"], 0)
        self.assertEqual(plan["timeline"][-1]["end_seconds"], 10)
        self.assertEqual(plan["canal"]["id"], "alchemy-lab")
        self.assertEqual(plan["modelo"]["id"], "camadas-animadas")
        self.assertFalse(plan["publishing"]["upload_enabled"])

    def test_invalid_duration_is_rejected(self):
        self.config["video"]["duration_seconds"] = 9
        with self.assertRaises(ValueError):
            build_storyboard(self.config)

    def test_duplicate_scene_id_is_rejected(self):
        self.config["scenes"][1]["id"] = self.config["scenes"][0]["id"]
        with self.assertRaises(ValueError):
            build_storyboard(self.config)

    def test_video_can_override_channel_model(self):
        channel = {"modelo_padrao": "camadas-animadas"}
        video = {"modelo": "imagem-estatica"}
        model = resolve_model(channel, video, ROOT / "modelos")
        self.assertEqual(model["id"], "imagem-estatica")
        self.assertEqual(model["etapas"]["animacao"]["modo"], "zoom-pan")

    def test_channel_model_is_used_when_video_does_not_override(self):
        channel = {"modelo_padrao": "camadas-animadas"}
        model = resolve_model(channel, {}, ROOT / "modelos")
        self.assertEqual(model["id"], "camadas-animadas")

    def test_unknown_model_fails_instead_of_falling_back(self):
        with self.assertRaises(ValueError):
            resolve_model({"modelo_padrao": "camadas-animadas"}, {"modelo": "inexistente"}, ROOT / "modelos")

    def test_model_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_model({"modelo_padrao": "camadas-animadas"}, {"modelo": "../secrets"}, ROOT / "modelos")

    def test_video_path_outside_channel_is_rejected(self):
        with self.assertRaises(ValueError):
            load_video_config("README.md", root=ROOT)


if __name__ == "__main__":
    unittest.main()
