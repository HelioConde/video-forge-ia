import json
import unittest
from pathlib import Path

from videoforge.pipeline import build_storyboard


ROOT = Path(__file__).resolve().parents[1]


class StoryboardTest(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(
            (ROOT / "config" / "example.json").read_text(encoding="utf-8")
        )

    def test_timeline_for_ten_seconds(self):
        plan = build_storyboard(self.config)
        self.assertEqual(plan["video"]["duration_seconds"], 10)
        self.assertEqual(len(plan["timeline"]), 2)
        self.assertEqual(plan["timeline"][0]["start_seconds"], 0)
        self.assertEqual(plan["timeline"][-1]["end_seconds"], 10)
        self.assertFalse(plan["publishing"]["upload_enabled"])

    def test_invalid_duration_is_rejected(self):
        self.config["video"]["duration_seconds"] = 9
        with self.assertRaises(ValueError):
            build_storyboard(self.config)

    def test_duplicate_scene_id_is_rejected(self):
        self.config["scenes"][1]["id"] = self.config["scenes"][0]["id"]
        with self.assertRaises(ValueError):
            build_storyboard(self.config)


if __name__ == "__main__":
    unittest.main()
