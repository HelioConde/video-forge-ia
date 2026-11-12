"""Offline handoff tests: source research provenance and human topic reservation."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from videoforge.production.editorial_handoff import (
    HandoffError, prepare_editorial_handoff,
)
from videoforge.production.dispatcher import ROOT


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for rel in ("agentes/equipe.json", "agentes/gerentes-canais.json",
                    "canal/otaku-br/canal.json",
                    "canal/otaku-br/editorial/reservas.json"):
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dst)
        self.source_id = "43112345678"
        self.topic = {
            "id": "agente-ideia-01",
            "anime": "One Piece",
            "title": "Um mistério original sobre os personagens de One Piece",
            "angle": "comparar pistas verificáveis",
            "genre": "análise",
            "format": "curta análise autoral",
            "duration_seconds": 90,
            "rationale": "hipótese baseada nos dados",
            "sources_to_verify": ["fonte primária pendente"],
        }
        self.report = {
            "schema": "videoforge/editorial-team/v1",
            "channel": "otaku-br",
            "channel_id": "UCXGYTuBYn-0Ziqin5ajKhOw",
            "status": "awaiting_editorial_review_and_reservation",
            "decision_authority": "Gerente Otaku Multicena",
            "topic_provenance": "codex_proxy_researcher_plus_real_youtube_analytics",
            "choices_from_assistant": 0,
            "requires_human_editorial_review": True,
            "requires_topic_reservation": True,
            "proxy_calls": 1,
            "images_generated": 0,
            "video_generated": False,
            "upload_enabled": False,
            "chosen_topic": self.topic,
            "deputy": {
                "role": "subgerente",
                "candidates": [{"candidate_id": self.topic["id"], "accepted": True}],
            },
            "proposals": [{
                "id": self.topic["id"],
                "title": self.topic["title"],
                "status": "eligible_for_manager_ranking",
            }],
        }

    def _reserve(self, *, approved=True, source=None):
        path = self.root / "canal/otaku-br/editorial/reservas.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["entries"] = [{
            "id": self.topic["id"],
            "source_run_id": source or self.source_id,
            "titulo_provisorio": self.topic["title"],
            "status": "approved_reserved" if approved else "proposed",
            "human_approved": bool(approved),
        }]
        path.write_text(json.dumps(doc), encoding="utf-8")

    def test_no_reservation_no_proxy_call(self):
        with self.assertRaisesRegex(HandoffError, "APPROVED_RESERVATION_REQUIRED"):
            prepare_editorial_handoff(self.report, source_run_id=self.source_id,
                                      root=self.root)

    def test_matching_approved_reservation_yields_only_briefing_plan(self):
        self._reserve()
        payload = prepare_editorial_handoff(
            self.report, source_run_id=self.source_id, root=self.root
        )
        self.assertTrue(payload["human_approved_reservation_verified"])
        self.assertEqual(payload["proxy_requests_sent"], 0)
        self.assertEqual(payload["task_id"], "briefing")
        self.assertEqual(len(payload["plan"]["tasks"]), 18)
        self.assertFalse(payload["plan"]["publishing_enabled"])
        self.assertFalse(payload["plan"]["execution_enabled"])
        context = json.loads(payload["context"])
        self.assertEqual(context["anime"], "One Piece")
        self.assertEqual(context["status"], "editorial_topic_reservation_verified")
        self.assertIn("sources_to_verify_not_yet_verified", context)

    def test_source_run_mismatch_or_unapproved_blocks(self):
        self._reserve(source="43112345679")
        with self.assertRaisesRegex(HandoffError, "APPROVED_RESERVATION_REQUIRED"):
            prepare_editorial_handoff(self.report, source_run_id=self.source_id,
                                      root=self.root)
        self._reserve(approved=False)
        with self.assertRaisesRegex(HandoffError, "APPROVED_RESERVATION_REQUIRED"):
            prepare_editorial_handoff(self.report, source_run_id=self.source_id,
                                      root=self.root)

    def test_forged_role_decision_or_deputy_audit_blocks(self):
        self._reserve()
        for edits, error in (
            ({"decision_authority": "ChatGPT"}, "UNVERIFIED_EDITORIAL_DECISION"),
            ({"topic_provenance": "assumed"}, "UNVERIFIED_EDITORIAL_DECISION"),
            ({"requires_human_editorial_review": False}, "UNVERIFIED_EDITORIAL_DECISION"),
            ({"upload_enabled": True}, "UNVERIFIED_EDITORIAL_DECISION"),
            ({"channel_id": "different"}, "UNVERIFIED_EDITORIAL_DECISION"),
            ({"deputy": {"role": "subgerente", "candidates": []}},
             "TOPIC_NOT_DEPUTY_APPROVED"),
        ):
            with self.subTest(edits=edits), self.assertRaisesRegex(HandoffError, error):
                candidate = copy.deepcopy(self.report)
                candidate.update(edits)
                prepare_editorial_handoff(candidate, source_run_id=self.source_id,
                                          root=self.root)

    def test_paused_anime_rejected_even_when_signed_off(self):
        self._reserve()
        report = copy.deepcopy(self.report)
        report["chosen_topic"]["anime"] = "Death Note"
        with self.assertRaisesRegex(HandoffError, "ANIME_PAUSED"):
            prepare_editorial_handoff(report, source_run_id=self.source_id,
                                      root=self.root)

    def test_no_unique_topic_cannot_be_run(self):
        self._reserve()
        report = copy.deepcopy(self.report)
        report["chosen_topic"] = None
        with self.assertRaisesRegex(HandoffError, "TOPIC_MISSING"):
            prepare_editorial_handoff(report, source_run_id=self.source_id,
                                      root=self.root)


if __name__ == "__main__":
    unittest.main()
