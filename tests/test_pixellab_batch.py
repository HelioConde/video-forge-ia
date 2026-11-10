"""Geração PixelLab em lote para Work: testes isolados sem rede/sem créditos."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videoforge.pixellab.batch import MAX_NEW, examine, plan, run
from videoforge.pixellab.client import PixelLabError

CHAR_ID = "123e4567-e89b-12d3-a456-426614174007"
GROUP_ID = "123e4567-e89b-12d3-a456-426614174000"
JOB_ID = "223e4567-e89b-12d3-a456-426614174001"


class Stub:
    def __init__(self, groups=None):
        self.groups = groups if groups is not None else []
        self.posts = []
        self.jobs = []

    def character(self, character_id):
        if character_id != CHAR_ID:
            raise AssertionError("Base incorreta")
        return {"animations": self.groups, "status": "completed"}

    def animate(self, character_id, *, name, description, direction,
                frame_count=4, animation_group_id=None):
        self.posts.append((name, direction, animation_group_id))
        if animation_group_id is not None:
            group = next(g for g in self.groups if g["animation_group_id"] == animation_group_id)
        else:
            group = {"animation_group_id": GROUP_ID, "display_name": name, "directions": []}
            self.groups.append(group)
        if direction in {r["direction"] for r in group["directions"]}:
            raise AssertionError("POST de duplicata")
        group["directions"].append({"direction": direction, "frames": [1,2,3,4]})
        return {"background_job_ids": [JOB_ID], "animation_group_id": group["animation_group_id"]}

    def poll(self, job_ids, *, max_seconds):
        self.jobs.extend(job_ids)

    def download(self, character_id, *, spritesheet):
        return b"PK\\x03\\x04demo"


class BatchTests(unittest.TestCase):
    def test_plan_skips_existing_direction_without_posts(self):
        fake = Stub([{"animation_group_id": GROUP_ID, "display_name": "walk",
                      "directions": [{"direction": "south"}, {"direction": "east"}]}])
        with tempfile.TemporaryDirectory() as td:
            report = run(fake, CHAR_ID, scope="walk", output=Path(td), max_new=4)
            self.assertEqual(report["existing_directions"], 2)
            self.assertEqual(report["missing_directions"], 6)
            self.assertEqual(len(report["selected"]), 4)
            self.assertEqual(report["submitted"], [])
            self.assertEqual(fake.posts, [])

    def test_generates_only_missing_and_extends_group(self):
        fake = Stub([{"animation_group_id": GROUP_ID, "animation_type": "walking",
                      "directions": [{"direction": "south"}]}])
        with tempfile.TemporaryDirectory() as td:
            report = run(fake, CHAR_ID, scope="walk", mode="generate", max_new=2,
                         authorized=True, public_artifacts=True, output=Path(td))
            self.assertEqual(len(fake.posts), 2)
            self.assertEqual(fake.posts[0], ("walk", "south-east", GROUP_ID))
            self.assertEqual(fake.posts[1], ("walk", "east", GROUP_ID))
            self.assertEqual(report["result"], "completed")
            self.assertEqual(len(fake.jobs), 2)
            saved = (Path(td) / "report.json").read_text(encoding="utf-8")
            self.assertNotIn(CHAR_ID, saved)
            self.assertNotIn(GROUP_ID, saved)
            self.assertNotIn(JOB_ID, saved)

    def test_reuses_group_created_during_same_batch(self):
        fake = Stub([])
        with tempfile.TemporaryDirectory() as td:
            report = run(fake, CHAR_ID, scope="idle", mode="generate", max_new=3,
                         authorized=True, public_artifacts=True, output=Path(td))
            self.assertEqual(len(fake.posts), 3)
            self.assertIsNone(fake.posts[0][2])
            self.assertEqual(fake.posts[1][2], GROUP_ID)
            self.assertEqual(fake.posts[2][2], GROUP_ID)
            self.assertEqual(len(report["completed"]), 3)

    def test_unknown_group_blocks_unsafe_generation(self):
        fake = Stub([{"animation_group_id": GROUP_ID, "display_name": "custom motion",
                      "directions": [{"direction": "south"}]}])
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PixelLabError):
                run(fake, CHAR_ID, scope="walk", mode="generate", max_new=2,
                    authorized=True, public_artifacts=True, output=Path(td))
            self.assertEqual(fake.posts, [])

    def test_unknown_group_can_be_explicitly_approved(self):
        fake = Stub([{"animation_group_id": GROUP_ID, "display_name": "jump",
                      "directions": [{"direction": "south"}]}])
        with tempfile.TemporaryDirectory() as td:
            report = run(fake, CHAR_ID, scope="idle", allow_unknown=True,
                         output=Path(td))
            self.assertEqual(report["missing_directions"], 8)
            self.assertEqual(report["unclassified_groups"], 1)

    def test_fails_closed_if_no_animation_list(self):
        with self.assertRaises(PixelLabError):
            examine({"animation_count": 10})

    def test_existing_group_without_id_is_not_extended(self):
        with self.assertRaises(PixelLabError):
            plan({"animations": [{"display_name": "walk",
                                  "directions": [{"direction": "south"}]}]},
                 ("walk",))

    def test_multiple_groups_same_name_block(self):
        groups = [{"animation_group_id": GROUP_ID, "display_name": "walk", "directions": []},
                  {"animation_group_id": JOB_ID, "display_name": "walking", "directions": []}]
        with self.assertRaises(PixelLabError):
            plan({"animations": groups}, ("walk",))

    def test_missing_authorization_prevents_posts(self):
        fake = Stub([])
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PixelLabError):
                run(fake, CHAR_ID, scope="walk", mode="generate", max_new=2,
                    output=Path(td))
            self.assertEqual(fake.posts, [])

    def test_invalid_max_new(self):
        fake = Stub([])
        with self.assertRaises(ValueError):
            run(fake, CHAR_ID, max_new=MAX_NEW+1)

    def test_export_only_after_authorized_generation(self):
        fake = Stub([])
        with tempfile.TemporaryDirectory() as td:
            run(fake, CHAR_ID, scope="idle", mode="generate", max_new=1,
                authorized=True, public_artifacts=True,
                export_zips=True, output=Path(td))
            self.assertTrue((Path(td)/"spritesheet.zip").exists())


if __name__ == "__main__":
    unittest.main()
