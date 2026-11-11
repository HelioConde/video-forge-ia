import json
import tempfile
import unittest
from pathlib import Path
from scripts.build_dashboard_data import make_snapshot

class DashboardTests(unittest.TestCase):
    def test_safe_config_only_snapshot(self):
        snapshot = make_snapshot()
        self.assertEqual(len(snapshot["canais"]), 5)
        self.assertEqual(len(snapshot["agentes"]), 8)
        self.assertEqual(len({c["gerente"]["id"] for c in snapshot["canais"]}), 5)
        self.assertTrue(all(c["gerente"]["status"] == "nao_conectado" for c in snapshot["canais"]))
        self.assertTrue(all(c["gerente"]["regra_antirrepeticao"] for c in snapshot["canais"]))
        self.assertEqual(next(c["gerente"]["nome"] for c in snapshot["canais"]
                              if c["id"] == "otaku-br"), "Gerente Otaku Multicena")
        self.assertEqual(len(snapshot["organizacao"]["departamentos"]), 5)
        self.assertEqual(snapshot["organizacao"]["especialistas_planejados"], 27)
        self.assertEqual(snapshot["organizacao"]["modelo"], "planejado_sem_ia")
        self.assertTrue(all(a["status"] == "nao_conectado" for a in snapshot["agentes"]))
        self.assertTrue(all(not a["conexao"]["modelo_definido"] for a in snapshot["agentes"]))
        self.assertTrue(all(not a["conexao"]["executor_habilitado"] for a in snapshot["agentes"]))
        self.assertEqual(next(a["conexao"]["dependencias"] for a in snapshot["agentes"]
                              if a["id"] == "editor"), ["animador", "narrador"])
        content = json.dumps(snapshot).lower()
        for sensitive in ("oauth_token", "refresh_token", "client_secret", "youtube_channel_id", "ucctyfe"):
            self.assertNotIn(sensitive, content)

    def test_accepts_only_known_agents_and_channels(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "events.json"
            p.write_text(json.dumps({"agents":[{"id":"roteirista","status":"aguardando","canal":"otaku-br","tarefa":"Na fila"}]}))
            snapshot = make_snapshot(events=p)
            self.assertEqual(next(a["status"] for a in snapshot["agentes"] if a["id"] == "roteirista"), "aguardando")
            p.write_text(json.dumps({"agents":[{"id":"roteirista","status":"trabalhando","canal":"otaku-br","tarefa":"Planejando"}]}))
            with self.assertRaises(ValueError):
                make_snapshot(events=p)
            p.write_text(json.dumps({"agents":[{"id":"fake","status":"trabalhando"}]}))
            with self.assertRaises(ValueError):
                make_snapshot(events=p)

if __name__ == "__main__":
    unittest.main()
