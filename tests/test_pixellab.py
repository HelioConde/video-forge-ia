import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videoforge.pixellab.client import PixelLabClient, PixelLabError
from videoforge.pixellab.cli import load_profile, parse_character_id, run, reference_image

ID_A = "123e4567-e89b-12d3-a456-426614174000"
ID_B = "223e4567-e89b-12d3-a456-426614174001"
ID_C = "323e4567-e89b-12d3-a456-426614174002"


class StubAPI:
    def __init__(self):
        self.events = []

    def create(self, *args, **kwargs):
        self.events.append("create")
        return {"character_id": ID_A, "background_job_id": ID_B}

    def animate(self, *args, **kwargs):
        self.events.append("animate")
        return {"background_job_ids": [ID_C], "animation_group_id": ID_B}

    def character(self, *args, **kwargs):
        self.events.append("character")
        return {"id": ID_A}

    def poll(self, job_ids):
        self.events.append("poll")
        return {job_id: {"status": "completed"} for job_id in job_ids}

    def download(self, *args, **kwargs):
        self.events.append("download")
        return b"PK\x03\x04" + b"x" * 10


class CharacterConfigTests(unittest.TestCase):
    def test_profile_and_motions_are_valid(self):
        p = load_profile("alex")
        self.assertLessEqual(len(p["description"]), 2000)
        self.assertIn("walk", p["motions"])
        self.assertEqual(p["size"], 64)

    def test_rejects_unsafe_character_or_id(self):
        with self.assertRaises(ValueError):
            load_profile("../../test")
        with self.assertRaises(ValueError):
            parse_character_id("foo/../../secret")
        with self.assertRaises(ValueError):
            parse_character_id("")

    def test_no_reference_by_default(self):
        self.assertIsNone(reference_image(load_profile("alex"), "alex"))

    def test_profile_reference_cannot_escape_folder(self):
        profile = load_profile("alex")
        profile["reference_file"] = "../../outside.png"
        with self.assertRaises(ValueError):
            reference_image(profile, "alex")


class PipelineTests(unittest.TestCase):
    def test_free_plan_never_uses_client(self):
        with tempfile.TemporaryDirectory() as td:
            with patch("videoforge.pixellab.cli.PixelLabClient", side_effect=AssertionError("API called")):
                info = run("create-and-animate", "alex", "walk", "south",
                           execute=False, output=Path(td))
            self.assertEqual(info["status"], "planned_only")
            self.assertTrue((Path(td) / "manifest.json").exists())

    def test_create_and_animate_only_two_paid_posts(self):
        with tempfile.TemporaryDirectory() as td:
            api = StubAPI()
            result = run("create-and-animate", "alex", "walk", "south",
                         execute=True, output=Path(td), client=api)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(api.events.count("create"), 1)
            self.assertEqual(api.events.count("animate"), 1)
            self.assertEqual(api.events.count("poll"), 2)
            self.assertEqual(api.events.count("download"), 2)
            self.assertTrue((Path(td) / "spritesheet.zip").exists())

    def test_ensure_reuses_existing_character(self):
        with tempfile.TemporaryDirectory() as td:
            api = StubAPI()
            run("ensure-and-animate", "alex", "type", "east",
                execute=True, character_id=ID_A, output=Path(td), client=api)
            self.assertNotIn("create", api.events)
            self.assertIn("animate", api.events)

    def test_animate_needs_existing_id(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PixelLabError):
                run("animate", "alex", "walk", "south",
                    execute=True, output=Path(td), client=StubAPI())

    def test_invalid_motion_is_rejected_before_cost(self):
        with self.assertRaises(ValueError):
            run("create", "alex", "fly", "south", execute=False)

    def test_manifest_saves_job_before_poll(self):
        class FailingStub(StubAPI):
            def poll(self, jobs):
                raise PixelLabError("Simulated failure")
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PixelLabError):
                run("create", "alex", "idle", "south",
                    execute=True, client=FailingStub(), output=Path(td))
            data = json.loads((Path(td) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "creation_pending")
            self.assertEqual(data["creation_job_id"], ID_B)


class ClientTests(unittest.TestCase):
    def test_token_is_required(self):
        with self.assertRaises(PixelLabError):
            PixelLabClient("")

    def test_rejects_dynamic_host_paths(self):
        client = PixelLabClient("fake")
        for path in ("https://example.com/a", "//evil.com", "/../secret", "/characters/?x=y"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                client._request("GET", path)

    def test_poll_success_without_network(self):
        client = PixelLabClient("fake")
        client.job = lambda job_id: {"status": "completed"}
        values = iter([0.0, 0.1])
        r = client.poll([ID_A], clock=lambda: next(values), sleeper=lambda n: None)
        self.assertEqual(r[ID_A]["status"], "completed")

    def test_poll_stops_on_failed(self):
        client = PixelLabClient("fake")
        client.job = lambda job_id: {"status": "failed"}
        with self.assertRaises(PixelLabError):
            client.poll([ID_A], clock=lambda: 0, sleeper=lambda n: None)


if __name__ == "__main__":
    unittest.main()
