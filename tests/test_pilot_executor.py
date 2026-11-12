"""Offline production tests. Zero OAuth, AI requests, uploads, or FFmpeg."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videoforge.production.dispatcher import build_plan, STAGES
from videoforge.production.pilot_executor import (
    CallBudget, FALLBACK, LIMIT, PilotError, STAGE_FILES, validate_story,
    generate_story, produce,
)


class FakeProxy:
    def __init__(self, *, eligible=True, response=None):
        self.eligible = eligible
        self.response = response
        self.chat_requests = []

    def accounts(self):
        return {"accounts": [{"eligible_now": self.eligible}]}

    def chat(self, body):
        self.chat_requests.append(body)
        return self.response if self.response is not None else {}


class PilotContracts(unittest.TestCase):
    def test_budget_strict_hard_maximum(self):
        budget = CallBudget(4)
        for _ in range(4):
            budget.use()
        self.assertEqual(budget.sent, 4)
        with self.assertRaises(PilotError):
            budget.use()
        with self.assertRaises(PilotError):
            CallBudget(0)
        with self.assertRaises(PilotError):
            CallBudget(LIMIT + 1)

    def test_original_story_contract(self):
        result = validate_story(FALLBACK)
        self.assertEqual(len(result["scenes"]), 3)
        self.assertEqual(len(result["tags"]), 3)
        self.assertIn("cavaleiro", result["scenes"][0]["narration"])

    def test_reject_franchises_and_extra_scenes(self):
        story = dict(FALLBACK)
        story["title"] = "Naruto and the paper knight"
        with self.assertRaises(PilotError):
            validate_story(story)
        story = dict(FALLBACK)
        story["scenes"] = story["scenes"] * 2
        with self.assertRaises(PilotError):
            validate_story(story)

    def test_bad_chat_result_fails_closed_without_story_fallback(self):
        proxy = FakeProxy()
        budget = CallBudget(4)
        with self.assertRaisesRegex(PilotError, "SCRIPT_GENERATION_UNAVAILABLE"):
            generate_story(proxy, budget, "gpt-6.1-sol")
        self.assertEqual(budget.sent, 1)
        self.assertEqual(len(proxy.chat_requests), 1)

    def test_image_policy_is_explicit_and_rejects_local_fallback(self):
        from videoforge.production.image_policy import (
            load_image_policy, validate_generated_visuals, ImageProvenanceError
        )
        p = load_image_policy()
        self.assertEqual(p["mode"], "generator_only")
        self.assertIs(p["assistant_generated_images_allowed"], False)
        self.assertIs(p["local_fallback_allowed"], False)
        self.assertEqual(p["on_failure"], "abort_video")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ImageProvenanceError, "MISSING_GENERATED_SCENES"):
                validate_generated_visuals([], Path(tmp), expected_count=3)
            forged = [{"scene": 1, "file": "scene-1.png",
                       "origin": "local_original_fallback",
                       "generated_by": "video_forge_image_generator"}]
            with self.assertRaisesRegex(ImageProvenanceError, "UNTRUSTED_VISUAL_OR_FALLBACK"):
                validate_generated_visuals(forged, Path(tmp), expected_count=1)

    def test_image_provider_failure_must_abort_before_video_render(self):
        from videoforge.production.pilot_executor import visuals
        from videoforge.proxy.client import ProxyError
        class ImageFailProxy:
            def images_generate(self, body):
                raise ProxyError("Codex Proxy HTTP 429")
        with tempfile.TemporaryDirectory() as tmp:
            budget = CallBudget(4)
            budget.use()  # script stage
            with self.assertRaisesRegex(PilotError, "IMAGE_GENERATOR_UNAVAILABLE"):
                visuals(ImageFailProxy(), budget, Path(tmp), validate_story(FALLBACK),
                        "gpt-image-2")
            self.assertEqual(budget.sent, 2)
            self.assertFalse((Path(tmp)/"video.mp4").exists())
            self.assertFalse((Path(tmp)/"scene-1.png").exists())

    def test_invalid_image_response_never_creates_placeholder(self):
        from videoforge.production.pilot_executor import visuals
        class InvalidImageProxy:
            def images_generate(self, body):
                return {"data": [{"b64_json": "invalid-image-base64"}]}
        with tempfile.TemporaryDirectory() as tmp:
            budget = CallBudget(4)
            budget.use()
            with self.assertRaisesRegex(PilotError, "IMAGE_GENERATOR_RETURNED_INVALID_MEDIA"):
                visuals(InvalidImageProxy(), budget, Path(tmp), validate_story(FALLBACK),
                        "gpt-image-2")
            self.assertFalse((Path(tmp)/"video.mp4").exists())

    def test_all_scenes_must_fit_budget_before_first_image_request(self):
        from videoforge.production.pilot_executor import visuals
        class NoCallProxy:
            def images_generate(self, body):
                raise AssertionError("not allowed to call provider with incomplete budget")
        with tempfile.TemporaryDirectory() as tmp:
            budget = CallBudget(3)
            budget.use()
            with self.assertRaisesRegex(PilotError, "INSUFFICIENT_BUDGET"):
                visuals(NoCallProxy(), budget, Path(tmp), validate_story(FALLBACK),
                        "gpt-image-2")
            self.assertEqual(budget.sent, 1)

    def test_all_specialists_accounted_and_human_release_blocked(self):
        self.assertEqual(len(STAGES), 18)
        self.assertEqual(len(STAGE_FILES), 15)
        self.assertEqual(
            set(STAGE_FILES) | {"qa_conteudo", "aprovacao", "publicacao"},
            {x[0] for x in STAGES}
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(__file__).resolve().parents[1]
            plan = build_plan({"id": "pilot-local-test", "canal": "otaku-br",
                               "tema": "original fantasy", "duracao_segundos": 18},
                              root=root)
            self.assertFalse(plan["publishing_enabled"])
            self.assertEqual(len(plan["tasks"]), 18)

    def test_no_production_without_explicit_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"VIDEOFORGE_PILOT_APPROVED": ""}):
                with self.assertRaisesRegex(PilotError, "OWNER_APPROVAL_REQUIRED"):
                    produce(Path(tmp)/"pilot", "pilot-local", client=FakeProxy())

    def test_no_eligible_account_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)/"pilot"
            with patch.dict("os.environ", {"VIDEOFORGE_PILOT_APPROVED": "yes"}):
                with self.assertRaisesRegex(PilotError, "NO_ELIGIBLE_PROXY_ACCOUNT"):
                    produce(dest, "pilot-local", client=FakeProxy(eligible=False))
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
