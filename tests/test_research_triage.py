"""Read-only external-research assessment, no topics, no Proxy or video."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from videoforge.channel_agents.external_research import latest_research
from videoforge.channel_agents.manager import channel_policy
from videoforge.channel_agents.research_triage import (
    ResearchTriageError, _matched_title, main, triage_research,
)

ROOT = Path(__file__).resolve().parents[1]
CID = "UCXGYTuBYn-0Ziqin5ajKhOw"


def make_snapshot():
    rows = [
        ("jojo1", "JoJo Steel Ball Run curiosidades", 120, 88),
        ("jojo2", "Análise do episódio 8 de Steel Ball Run", 60, 71),
        ("op001", "One Piece: teorias de Elbaf", 300, 67),
        ("bc001", "Black Clover Asta e o poder desconhecido", 22, 43),
        ("other", "Nova análise de Demon Slayer", 600, 65),
    ]
    return {
        "schema": "videoforge/channel-research/v1",
        "source": "youtube-data-v3+analytics-v2",
        "channel_id": CID,
        "read_only": True,
        "history_complete": True,
        "window": {"start": "2026-08-15", "end": "2026-11-12", "days": 90},
        "count": len(rows),
        "videos": [{
            "id": ident, "title": title, "duration_seconds": 100,
            "metrics": {
                "views": views,
                "averageViewPercentage": retention,
                "averageViewDuration": 75,
            },
        } for ident, title, views, retention in rows],
    }


class ResearchTriageTests(TestCase):
    def setUp(self):
        self.policy = channel_policy("otaku-br")
        self.packet = latest_research(root=ROOT, channel="otaku-br",
                                      channel_id=CID,
                                      as_of=date(2026, 11, 12))
        self.assertIsNotNone(self.packet)

    def test_public_sources_crosschecked_not_promoted_to_a_topic(self):
        report = triage_research(research=self.packet,
                                 snapshot=make_snapshot(), policy=self.policy)
        self.assertEqual(report["schema"], "videoforge/external-research-triage/v1")
        self.assertEqual(report["channel_id"], CID)
        self.assertTrue(report["verified_full_upload_history"])
        self.assertEqual(report["candidates_created"], 0)
        self.assertIsNone(report["selected"])
        self.assertEqual(report["topics_reserved"], 0)
        self.assertEqual(report["proxy_calls"], 0)
        self.assertFalse(report["publish_enabled"])
        self.assertEqual(len(report["signals"]), 3)
        by_id = {x["signal_id"]: x for x in report["signals"]}
        self.assertEqual(by_id["jojo-sbr-ep8-noticias-nov"]["series_title_mentions"], 2)
        self.assertEqual(by_id["jojo-sbr-ep8-noticias-nov"]
                         ["analytics_samples_with_minimum_fields"], 2)
        self.assertEqual(by_id["one-piece-elbaph-bluray-nov"]["series_title_mentions"], 1)
        self.assertEqual(by_id["black-clover-season2-outono2026"]["series_title_mentions"], 1)
        self.assertEqual(by_id["black-clover-season2-outono2026"]
                         ["analytics_samples_with_minimum_fields"], 0)
        self.assertTrue(all(x["topic_uniqueness"] ==
                            "not_verified_no_candidate_provided"
                            for x in report["signals"]))

    def test_no_substring_collision_or_unsubstantiated_analytics(self):
        self.assertFalse(_matched_title("JoJoJo memes", ["JoJo"]))
        self.assertTrue(_matched_title("JoJo: parte 7", ["JoJo"]))
        snapshot = make_snapshot()
        for x in snapshot["videos"]:
            x["metrics"] = {}
        report = triage_research(research=self.packet,
                                 snapshot=snapshot, policy=self.policy)
        self.assertEqual(report["overall_duration_evidence_confidence"],
                         "insufficient_data")
        self.assertIsNone(report["selected"])

    def test_rejects_wrong_channel_or_incomplete_youtube_inventory(self):
        snapshot = make_snapshot()
        for modification in (
            lambda s: s.update({"history_complete": False}),
            lambda s: s.update({"count": 2}),
            lambda s: s.update({"channel_id": "UCwrong"}),
            lambda s: s.update({"source": "synthetic-dryrun"}),
            lambda s: s.update({"read_only": False}),
        ):
            attempt = dict(snapshot)
            modification(attempt)
            with self.subTest(attempt=attempt.get("source")):
                with self.assertRaisesRegex(ResearchTriageError,
                                            "TRIAGE_VERIFIED_HISTORY_REQUIRED"):
                    triage_research(research=self.packet, snapshot=attempt,
                                    policy=self.policy)

    def test_source_aliases_are_validated_not_presumed_unique_topics(self):
        bad = json.loads(json.dumps(self.packet))
        bad["signals"][0]["title_aliases"] = ["JoJo", "jojo"]
        with self.assertRaisesRegex(ValueError, "RESEARCH_TITLE_ALIASES_INVALID"):
            triage_research(research=bad, snapshot=make_snapshot(),
                            policy=self.policy)

    def test_cli_offline_never_contacts_proxy_or_writes_video(self):
        with TemporaryDirectory() as temp:
            inventory = Path(temp) / "inventory.json"
            output = Path(temp) / "triage.json"
            inventory.write_text(json.dumps(make_snapshot()), encoding="utf-8")
            with mock.patch("videoforge.channel_agents.research_triage.oauth_access_token",
                            side_effect=AssertionError("OAuth called offline")):
                code = main(["--channel", "otaku-br", "--mode", "offline",
                             "--inventory", str(inventory), "--output", str(output)])
            self.assertEqual(code, 0)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["proxy_calls"], 0)
            self.assertEqual(data["candidates_created"], 0)
            self.assertEqual(data["videos_generated"], 0)
            self.assertFalse(data["publish_enabled"])
            with self.assertRaisesRegex(SystemExit, "TRIAGE_OUTPUT_ALREADY_EXISTS"):
                main(["--channel", "otaku-br", "--inventory", str(inventory),
                      "--output", str(output)])


if __name__ == "__main__":
    import unittest
    unittest.main()
