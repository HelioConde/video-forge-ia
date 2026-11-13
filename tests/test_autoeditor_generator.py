"""AutoEditorVideo generator contracts; ZERO AI, TTS, Remotion or upload."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from videoforge.generators import build_generator_plan, load_generator
from videoforge.generators.autoeditor import (
    AUTOEDITOR_COMMIT, AutoEditorBlocked, IMAGE_MODEL, MAX_IMAGES,
    build_remotion_props, generate_images, load_manifest, plan, produce,
    real_timing, validate_manifest,
)
from videoforge.proxy.client import ProxyError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "geradores/autoeditor/exemplo-manifesto.json"


class ErrorProxy:
    def __init__(self):
        self.calls = 0

    def images_generate(self, body):
        self.calls += 1
        raise ProxyError("Codex Proxy HTTP 429")


class TestAutoEditorGenerator(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest(EXAMPLE)

    def test_registered_pipeline_and_real_engine_identity(self):
        g = load_generator("autoeditor")
        self.assertEqual(g["status"], "ready_for_backend")
        self.assertFalse(g["execution_enabled"])
        p = build_generator_plan(g)
        operations = [x["operation"] for x in p["tasks"]]
        self.assertIn("image-generation", operations)
        self.assertIn("narration", operations)
        self.assertIn("captions", operations)
        self.assertIn("render", operations)
        self.assertIn("quality-review", operations)
        self.assertFalse(p["auto_publish_enabled"])
        self.assertEqual(len(AUTOEDITOR_COMMIT), 40)

    def test_plan_has_no_execution_and_no_generated_media(self):
        p = plan(self.manifest)
        self.assertEqual(p["channel"], "otaku-br")
        self.assertEqual(p["planned_image_calls"], 26)
        self.assertEqual(p["planned_layer_image_calls"], 18)
        self.assertEqual(p["expected_duration_seconds"], 90)
        self.assertEqual(p["actual_images_generated"], 0)
        self.assertFalse(p["execution_enabled"])
        self.assertFalse(p["youtube_uploaded"])

    def test_manifest_has_original_story_and_safe_contract(self):
        self.assertEqual(len(self.manifest["cenas"]), 8)
        self.assertEqual(self.manifest["modelo_imagem"], IMAGE_MODEL)
        self.assertEqual(self.manifest["formato"], "short-90s")
        self.assertFalse(self.manifest["upload_habilitado"])
        self.assertTrue(self.manifest["aprovacao_humana_obrigatoria"])

    def test_spy_family_provisional_preview_manifest_is_offline_and_within_budget(self):
        path = (ROOT / "canal" / "otaku-br" / "videos" /
                "spy-family-2027-preview-rascunho" / "manifest.json")
        preview = load_manifest(path)
        proposed = plan(preview)
        self.assertEqual(preview["canal"], "otaku-br")
        self.assertEqual(preview["id"], "spy-family-2027-preview-rascunho")
        self.assertEqual(len(preview["cenas"]), 6)
        self.assertEqual(proposed["planned_image_calls"], 12)
        self.assertEqual(proposed["planned_master_scenes"], 6)
        self.assertEqual(proposed["planned_layer_image_calls"], 6)
        self.assertEqual(preview["visual_lock"]["anchor_scene"], 1)
        self.assertTrue(preview["visual_lock"]["require_human_visual_review"])
        self.assertTrue(preview["aprovacao_humana_obrigatoria"])
        self.assertFalse(preview["upload_habilitado"])
        self.assertFalse(proposed["execution_enabled"])
        self.assertEqual(proposed["actual_images_generated"], 0)
        self.assertEqual(proposed["expected_duration_seconds"], 90)
        self.assertTrue(all(
            len(scene["layer_plan"]["characters"]) <= 1
            and not scene["layer_plan"]["movable_props"]
            for scene in preview["cenas"]
        ))

    def test_reject_unsanctioned_upload_and_non_generated_imagery(self):
        for key,value,expected in [
            ("upload_habilitado", True, "UPLOAD_MUST_BE_DISABLED"),
            ("origem_imagens","assistant-image", "GENERATOR_IMAGES_REQUIRED"),
            ("modelo_imagem","gpt-image-1.5", "IMAGE_MODEL_NOT_APPROVED"),
            ("formato","video-longo","ONLY_90S_SHORTS_IMPLEMENTED"),
            ("aprovacao_humana_obrigatoria",False,"HUMAN_QA_REQUIRED"),
            ("voz","en-US-AndrewNeural","VOICE_INVALID"),
            ("canal","../../.secrets","INVALID_CHANNEL_ID"),
        ]:
            with self.subTest(key=key):
                data=copy.deepcopy(self.manifest)
                data[key]=value
                with self.assertRaisesRegex(AutoEditorBlocked,expected):
                    validate_manifest(data)

    def test_fails_closed_for_kids_classification_and_duplicate_scene_ids(self):
        data=copy.deepcopy(self.manifest)
        data["canal"]="manu-kids"
        data["feito_para_criancas"]=False
        with self.assertRaisesRegex(AutoEditorBlocked,"KIDS_CLASSIFICATION_REQUIRED"):
            validate_manifest(data)
        data=copy.deepcopy(self.manifest)
        data["cenas"][1]["id"]=data["cenas"][0]["id"]
        with self.assertRaisesRegex(AutoEditorBlocked,"DUPLICATED_SCENE_ID"):
            validate_manifest(data)

    def test_only_real_tts_word_markers_go_to_cuts(self):
        script=" ".join(s["narracao"] for s in self.manifest["cenas"])
        source=script.split()
        # Markers are test dictionaries, NOT synthesized audio or images.
        words=[{"start":0.3+i*.36, "end":.5+i*.36, "text":x}
               for i,x in enumerate(source)]
        duration=110.0
        bounds, captions=real_timing(self.manifest,words,duration)
        self.assertEqual(len(bounds),9)
        self.assertEqual(bounds[0],0)
        self.assertEqual(bounds[-1],3300)
        self.assertTrue(all(b>a for a,b in zip(bounds,bounds[1:])))
        self.assertGreater(len(captions),25)
        props=build_remotion_props(self.manifest,duration,words,
                                   staging_id="vf-autoeditor-test")
        self.assertEqual(props["durationFrames"],3300)
        self.assertEqual(len(props["scenes"]),8)
        self.assertEqual(props["scenes"][0]["renderMode"],"master_static")
        self.assertEqual(props["audio"],"generated/vf-autoeditor-test/voice.mp3")
        self.assertTrue(props["captions"])

    def test_render_never_starts_without_explicit_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"pilot"
            with patch.dict(os.environ,{"VIDEOFORGE_AUTOEDITOR_RENDER_AUTHORIZED":""}):
                with self.assertRaisesRegex(AutoEditorBlocked,
                                            "EXPLICIT_RENDER_APPROVAL_REQUIRED"):
                    produce(self.manifest,destination=dest,
                            motion_root=Path(tmp),job_id="preview-01",
                            max_calls=8,proxy=ErrorProxy())
            self.assertFalse(dest.exists())

    def test_proxy_429_never_creates_fallback_scene(self):
        proxy=ErrorProxy()
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            with self.assertRaisesRegex(AutoEditorBlocked,"HTTP 429"):
                generate_images(self.manifest,folder,proxy,max_calls=8)
            self.assertEqual(proxy.calls,1)
            self.assertEqual(list(folder.iterdir()),[])

    def test_insufficient_image_budget_blocks_before_one_request(self):
        proxy=ErrorProxy()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(AutoEditorBlocked,"BUDGET_INSUFFICIENT"):
                generate_images(self.manifest,Path(tmp),proxy,max_calls=7)
            self.assertEqual(proxy.calls,0)

    def test_fresh_proxy_quota_restriction_blocks_before_tts_or_image_calls(self):
        from datetime import datetime, timezone
        class CachedProxy:
            calls = 0
            def accounts(self):
                self.calls += 1
                return {"accounts": [{
                    "eligible_now": True,
                    "cached_quota": {
                        "rate_limit": {"allowed": False, "limit_reached": True},
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "cooldown_until": None,
                }]}
        client = CachedProxy()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "pilot"
            with patch.dict(os.environ, {"VIDEOFORGE_AUTOEDITOR_RENDER_AUTHORIZED": "yes"}):
                with self.assertRaisesRegex(AutoEditorBlocked,
                                            "PROXY_FRESH_QUOTA_RESTRICTION"):
                    produce(self.manifest, destination=dest, motion_root=Path(tmp),
                            job_id="otaku-safe", max_calls=26, proxy=client)
            self.assertEqual(client.calls, 1)
            self.assertFalse(dest.exists())

    def test_proxy_account_cooldown_blocks_without_cached_usage_or_tts(self):
        from datetime import datetime, timedelta, timezone
        class CooldownProxy:
            def accounts(self):
                return {"accounts": [{
                    "eligible_now": True,
                    "cached_quota": None,
                    "cooldown_until": (datetime.now(timezone.utc) +
                                       timedelta(minutes=12)).isoformat(),
                }]}
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "pilot"
            with patch.dict(os.environ, {"VIDEOFORGE_AUTOEDITOR_RENDER_AUTHORIZED": "yes"}):
                with self.assertRaisesRegex(AutoEditorBlocked,
                                            "PROXY_ACCOUNT_COOLDOWN_ACTIVE"):
                    produce(self.manifest, destination=dest, motion_root=Path(tmp),
                            job_id="otaku-safe", max_calls=26,
                            proxy=CooldownProxy())
            self.assertFalse(dest.exists())

    def test_unknown_quota_is_not_mistaken_for_proven_clearance(self):
        from videoforge.proxy.quota_diagnostic import summarize_quota
        class UnobservedProxy:
            def accounts(self):
                return {"accounts": [{
                    "eligible_now": True, "cached_quota": None,
                    "cooldown_until": None,
                }]}
        report = summarize_quota(UnobservedProxy(), usage_mode="cached")
        self.assertEqual(report["status"], "quota_not_observed")
        self.assertFalse(report["429_cause_proven"])
        self.assertEqual(report["text_generations"], 0)

    def test_no_arbitrary_source_file_on_bad_manifest_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad=Path(tmp)/"bad.json"
            bad.write_text('{"schema":"invalid"}',encoding="utf-8")
            with self.assertRaisesRegex(AutoEditorBlocked,"MANIFEST_SCHEMA_INVALID"):
                load_manifest(bad)


if __name__ == "__main__":
    unittest.main()
