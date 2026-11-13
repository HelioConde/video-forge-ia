"""All channel information has its own namespace. No network or IA."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from videoforge.channel_agents.storage import (
    ChannelStorageError, channel_output_file, channel_output_root,
)


class ChannelStorageTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for channel in ("otaku-br", "gamer"):
            folder = self.root / "canal" / channel
            folder.mkdir(parents=True)
            (folder / "canal.json").write_text(
                json.dumps({"id": channel}), encoding="utf-8")

    def test_different_channels_never_share_output(self):
        otaku = channel_output_root("otaku-br", root=self.root)
        gamer = channel_output_root("gamer", root=self.root)
        self.assertNotEqual(otaku, gamer)
        for channel in ("otaku-br", "gamer"):
            file = self.root / "output" / channel / "editorial" / "plano.json"
            self.assertEqual(channel_output_file(channel, file, root=self.root), file)
            with self.assertRaisesRegex(ChannelStorageError, "CROSS_CHANNEL_PATH"):
                channel_output_file("gamer" if channel == "otaku-br" else "otaku-br",
                                    file, root=self.root)

    def test_private_runner_output_is_channel_scoped(self):
        base = self.root / "runner-private"
        expected = base / "otaku-br" / "editorial" / "relatorio.json"
        self.assertEqual(channel_output_file("otaku-br", expected, root=self.root,
                                             private_base=base), expected)
        with self.assertRaisesRegex(ChannelStorageError, "CROSS_CHANNEL_PATH"):
            channel_output_file("gamer", expected, root=self.root, private_base=base)

    def test_invalid_registration_traversal_and_symlink_blocked(self):
        for channel in ("../gamer", "invalid", "", "Otaku-Br"):
            with self.subTest(channel=channel), self.assertRaises(ChannelStorageError):
                channel_output_root(channel, root=self.root)
        with self.assertRaisesRegex(ChannelStorageError, "CROSS_CHANNEL_PATH"):
            channel_output_file("otaku-br", self.root / "output" / "otaku-br" /
                                "editorial" / ".." / ".." / "gamer" / "steal.json",
                                root=self.root)
        destination = self.root / "output" / "otaku-br" / "editorial"
        destination.mkdir(parents=True)
        (destination / "link").symlink_to(destination, target_is_directory=True)
        with self.assertRaisesRegex(ChannelStorageError, "SYMLINK_NOT_ALLOWED"):
            channel_output_file("otaku-br", destination / "link" / "file.json",
                                root=self.root)

    def test_operational_workflows_are_scoped_and_protected(self):
        root = Path(__file__).resolve().parents[1]
        editorial = (root / ".github/workflows/editorial-team-research.yml"
                     ).read_text(encoding="utf-8")
        manager = (root / ".github/workflows/channel-manager-analysis.yml"
                   ).read_text(encoding="utf-8")
        render = (root / ".github/workflows/autoeditor-generator.yml"
                  ).read_text(encoding="utf-8")
        self.assertIn("output/otaku-br/editorial/decisao.json", editorial)
        self.assertNotIn("output/editorial-team/decisao.json", editorial)
        self.assertIn("videoforge-channels/otaku-br/editorial", editorial)
        self.assertIn("secure_report encrypt", editorial)
        self.assertIn("videoforge-channels/$TARGET_CHANNEL/editorial", manager)
        self.assertIn("channel_output_root(obj[\"channel\"], root=root)", render)
        self.assertIn("env.write(\"VIDEOFORGE_CHANNEL=\"+manifest[\"canal\"]", render)
        self.assertIn("output/$VIDEOFORGE_CHANNEL/videos/", render)
        self.assertIn("output/*/videos/autoeditor-vf-", render)
        self.assertNotIn("output/autoeditor-vf-", render)
        self.assertIn("inputs.authorize_render == true", render)
        self.assertIn("github.event_name == 'workflow_dispatch'", render)

    def test_channel_config_mismatch_blocks(self):
        path = self.root / "canal" / "gamer" / "canal.json"
        path.write_text(json.dumps({"id": "otaku-br"}), encoding="utf-8")
        with self.assertRaisesRegex(ChannelStorageError, "CONFIG_MISMATCH"):
            channel_output_root("gamer", root=self.root)
