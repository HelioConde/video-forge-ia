"""External research packets are public context, never proof of YouTube demand."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from videoforge.channel_agents.external_research import (
    ExternalResearchError, latest_research, validate_research,
)

ROOT = Path(__file__).resolve().parents[1]
CID = "UCXGYTuBYn-0Ziqin5ajKhOw"


def valid_packet():
    return {
        "schema": "videoforge/external-editorial-research/v1",
        "channel": "otaku-br",
        "channel_id": CID,
        "researched_on": "2026-11-12",
        "prepared_by": "chatgpt_external_research",
        "scope": "source_context_only",
        "signals": [{
            "id": "jojo-story-2026",
            "series": "Steel Ball Run",
            "verified_fact": "O portal publicou atualizacao do episodio oito.",
            "research_question": "Vale uma analise original?",
            "editorial_status": "unranked_requires_channel_metrics",
            "source": {
                "publisher": "JoJo Portal oficial",
                "url": "https://jojo-portal.com/en/anime/sbr/news/",
                "published_on": "2026-11-09",
            },
        }],
    }


class ExternalResearchTests(TestCase):
    def test_approved_current_packet_is_loadable_and_unranked(self):
        data = latest_research(root=ROOT, channel="otaku-br", channel_id=CID,
                               as_of=date(2026, 11, 12))
        self.assertEqual(data["prepared_by"], "chatgpt_external_research")
        self.assertEqual(data["scope"], "source_context_only")
        self.assertGreaterEqual(len(data["signals"]), 3)
        self.assertTrue(all(row["editorial_status"] ==
                            "unranked_requires_channel_metrics"
                            for row in data["signals"]))

    def test_wrong_channel_or_future_date_is_rejected(self):
        data = valid_packet()
        with self.assertRaisesRegex(ExternalResearchError, "CHANNEL_MISMATCH"):
            validate_research(data, channel="otaku-en", channel_id=CID,
                              as_of=date(2026, 11, 12))
        with self.assertRaisesRegex(ExternalResearchError, "DATE_INVALID"):
            validate_research(data, channel="otaku-br", channel_id=CID,
                              as_of=date(2026, 11, 11))

    def test_no_sources_or_fake_rank_or_duplicate_id_fails_closed(self):
        for change, message in (
            (lambda d: d["signals"][0]["source"].update(
                {"url": "http://localhost/private"}), "SOURCE_INVALID"),
            (lambda d: d["signals"][0].update(
                {"editorial_status": "already_approved"}), "CANNOT_RANK"),
            (lambda d: d["signals"].append(dict(d["signals"][0])),
             "SIGNAL_ID_INVALID"),
        ):
            data = valid_packet()
            change(data)
            with self.subTest(expected=message):
                with self.assertRaisesRegex(ExternalResearchError, message):
                    validate_research(data, channel="otaku-br", channel_id=CID,
                                      as_of=date(2026, 11, 12))

    def test_latest_rejects_corrupted_file_instead_of_silently_falling_back(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            base = root / "canal" / "otaku-br" / "editorial" / "pesquisas"
            base.mkdir(parents=True)
            (base / "2026-11-11.json").write_text(
                json.dumps({**valid_packet(), "researched_on": "2026-11-11"}),
                encoding="utf-8")
            (base / "2026-11-12.json").write_text("NOT JSON", encoding="utf-8")
            with self.assertRaisesRegex(ExternalResearchError, "FILE_INVALID"):
                latest_research(root=root, channel="otaku-br", channel_id=CID,
                                as_of=date(2026, 11, 12))

    def test_missing_packet_returns_none_without_inventing_data(self):
        with TemporaryDirectory() as folder:
            self.assertIsNone(latest_research(root=Path(folder),
                                              channel="otaku-br", channel_id=CID,
                                              as_of=date(2026, 11, 12)))


if __name__ == "__main__":
    import unittest
    unittest.main()
