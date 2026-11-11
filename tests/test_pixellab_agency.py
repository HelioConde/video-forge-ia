"""Testes offline: PixelLab não deve consumir créditos sem consentimento."""
from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from videoforge.pixellab.agency_scene import (
    PLAN, make_payload, png_dimensions, read_plan, reference_bytes, run,
)
from videoforge.pixellab.client import PixelLabError

JOB_ID = "123e4567-e89b-12d3-a456-426614174000"


class FakeClient:
    def __init__(self, png: bytes):
        self.png = png
        self.calls = []

    def _request(self, method, path, payload=None, **kwargs):
        self.calls.append((method, path, payload))
        if method == "POST" and path == "/generate-image-v2":
            return {"background_job_id": JOB_ID, "status": "processing"}
        if method == "GET" and path == "/background-jobs/" + JOB_ID:
            return {"status": "completed", "last_response": {"images": [
                {"base64": "data:image/png;base64," + base64.b64encode(self.png).decode()}
            ]}}
        raise AssertionError(f"Unexpected call: {method} {path}")


class AgencySceneTests(unittest.TestCase):
    def setUp(self):
        self.plan = read_plan()
        self.reference = reference_bytes(self.plan)

    def test_reference_is_real_png_and_checked(self):
        self.assertEqual(png_dimensions(self.reference), (128, 72))
        self.assertEqual(self.plan["reference_size"], {"width": 128, "height": 72})
        self.assertEqual(self.plan["image_size"], {"width": 688, "height": 384})

    def test_payload_has_reference_and_one_building(self):
        payload = make_payload(self.plan, self.reference)
        self.assertEqual(payload["no_background"], False)
        self.assertEqual(payload["reference_images"][0]["size"]["width"], 128)
        self.assertTrue(payload["reference_images"][0]["image"]["base64"].startswith("data:image/png;base64,"))
        self.assertIn("SINGLE continuous", payload["description"])
        self.assertIn("No humans", payload["description"])
        self.assertNotIn("PIXELLAB_API_TOKEN", json.dumps(payload))

    def test_plan_is_truly_free_without_client(self):
        with tempfile.TemporaryDirectory() as temp:
            report = run(mode="plan", output=Path(temp))
            self.assertEqual(report["new_paid_requests"], 0)
            self.assertEqual(report["state"], "ready")
            self.assertEqual(list(Path(temp).iterdir()), [Path(temp) / "report.json"])

    def test_rejects_generation_without_both_approvals(self):
        for cost, public in ((False, False), (True, False), (False, True)):
            fake = FakeClient(self.reference)
            with tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(PixelLabError):
                    run(fake, mode="generate", authorized=cost,
                        public_artifact_authorized=public, output=Path(temp))
                self.assertEqual(fake.calls, [])

    def test_generate_exactly_one_post_and_export_sanitized_png(self):
        fake = FakeClient(self.reference)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            report = run(fake, mode="generate", authorized=True,
                         public_artifact_authorized=True, output=output)
            self.assertEqual(report["state"], "generated_preview")
            self.assertEqual([method for method, _, _ in fake.calls], ["POST", "GET"])
            self.assertEqual((output / "scene.png").read_bytes(), self.reference)
            self.assertNotIn(JOB_ID, (output / "report.json").read_text())
            self.assertFalse((output / "report.json").read_text().count("base64"))

    def test_reference_tampering_blocks_post(self):
        fake = FakeClient(self.reference)
        with tempfile.TemporaryDirectory() as temp:
            plan = dict(self.plan)
            plan["reference_sha256"] = "0" * 64
            custom = Path(temp) / "plan.json"
            custom.write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaises(ValueError):
                run(fake, mode="generate", authorized=True,
                    public_artifact_authorized=True, plan_path=custom,
                    output=Path(temp) / "out")
            self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
