"""Testes gratuitos de retomada controlada de lote PixelLab."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videoforge.pixellab.complete import complete
from videoforge.pixellab.client import PixelLabError

CHAR = "123e4567-e89b-12d3-a456-426614174001"


class Fake:
    def __init__(self, existing):
        self.groups = [{
            "animation_type": "idle",
            "animation_group_id": "123e4567-e89b-12d3-a456-426614174000",
            "directions": [{"direction": x} for x in existing],
        }]
        self.calls = []

    def character(self, character_id):
        self.calls.append("GET")
        return {"animations": self.groups}

    def animate(self, character_id, *, name, description, direction,
                frame_count=4, animation_group_id=None):
        self.calls.append("POST")
        group = next((g for g in self.groups if g["animation_type"] == name), None)
        if group is None:
            group = {"animation_type": name, "animation_group_id":
                     "123e4567-e89b-12d3-a456-426614174000",
                     "directions": []}
            self.groups.append(group)
        group["directions"].append({"direction": direction})
        return {
            "animation_group_id": group["animation_group_id"],
            "background_job_ids": ["223e4567-e89b-12d3-a456-426614174001"]
        }

    def poll(self, job_ids, max_seconds=780):
        self.calls.append("POLL")


class ContinuationTests(unittest.TestCase):
    def test_rounds_and_max_total(self):
        # Inicia com apenas três direções já existentes.
        api = Fake(["south", "south-east", "east"])
        with tempfile.TemporaryDirectory() as td:
            r = complete(api, CHAR, max_total=5, batch_size=2, output=Path(td))
            self.assertEqual(r["created"], 5)
            self.assertEqual(api.calls.count("POST"), 5)
            self.assertTrue((Path(td)/"summary.json").is_file())
            self.assertTrue((Path(td)/"round-01"/"report.json").is_file())
            self.assertTrue((Path(td)/"round-03"/"report.json").is_file())

    def test_no_duplicate_for_finished(self):
        from videoforge.pixellab.cli import DIRECTIONS
        api = Fake(list(DIRECTIONS))
        # Não há tarefas idle, mas há mais 5 movimentos a preencher.
        with tempfile.TemporaryDirectory() as td:
            r = complete(api, CHAR, max_total=1, batch_size=1, output=Path(td))
            self.assertEqual(r["created"], 1)
            self.assertEqual(api.calls.count("POST"), 1)

    def test_rejects_high_limit(self):
        with self.assertRaises(ValueError):
            complete(Fake([]), CHAR, max_total=49)

    def test_report_does_not_expose_id(self):
        api = Fake([])
        with tempfile.TemporaryDirectory() as td:
            complete(api, CHAR, max_total=1, output=Path(td))
            s = (Path(td) / "summary.json").read_text()
            self.assertNotIn(CHAR, s)

    def test_unknown_group_fails_closed(self):
        api = Fake([])
        api.groups.append({"animation_group_id":"123e4567-e89b-12d3-a456-426614174099",
                           "animation_type":"custom", "directions":[]})
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PixelLabError):
                complete(api, CHAR, max_total=4, output=Path(td))
            self.assertEqual(api.calls.count("POST"), 0)


if __name__ == "__main__":
    unittest.main()
