import json
import tempfile
import unittest
from pathlib import Path
from scripts.build_dashboard_data import make_snapshot

class DashboardTests(unittest.TestCase):
    def test_safe_config_only_snapshot(self):
        snapshot = make_snapshot()
        self.assertEqual(len(snapshot["canais"]), 5)
        self.assertEqual(len(snapshot["agentes"]), 9)
        self.assertEqual(snapshot["agentes"][-1]["id"], "subgerente")
        self.assertEqual(snapshot["ranking_funcionarios"]["status"], "awaiting_verified_evidence")
        self.assertEqual(snapshot["ranking_funcionarios"]["ranking"], [])
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

    def test_external_research_is_visible_as_unapproved_context(self):
        snapshot = make_snapshot()
        otaku = next(c for c in snapshot["canais"] if c["id"] == "otaku-br")
        research = otaku["pesquisa_externa"]
        self.assertEqual(research["estado"],
                         "contexto_aguardando_checagem_e_metricas")
        self.assertEqual(research["data_pesquisa"], "2026-11-12")
        self.assertEqual(len(research["sinais"]), 6)
        self.assertEqual(len({x["id"] for x in research["sinais"]}), 6)
        self.assertFalse(research["pauta_escolhida"])
        self.assertFalse(research["aprovado_por_subgerente"])
        self.assertTrue(all(s["estado"] == "aguardando_checagem"
                            and s["url"].startswith("https://")
                            for s in research["sinais"]))
        self.assertTrue(all("pesquisa_externa" not in c
                            for c in snapshot["canais"] if c["id"] != "otaku-br"))
        serialized = json.dumps(snapshot).lower()
        for forbidden in ("ucxgytubyn", "refresh_token", "client_secret",
                          "proxy_accounts_json", "access_token"):
            self.assertNotIn(forbidden, serialized)

    def test_external_research_public_export_strips_url_query_secrets(self):
        from unittest import mock
        from videoforge.channel_agents.external_research import latest_research
        from scripts.build_dashboard_data import ROOT
        packet = latest_research(root=ROOT, channel="otaku-br",
                                 channel_id="UCXGYTuBYn-0Ziqin5ajKhOw")
        assert packet is not None
        altered = json.loads(json.dumps(packet))
        altered["signals"][0]["source"]["url"] += "?access_token=PRIVATE_TEST"
        def source_for_channel(*, channel, **_):
            return altered if channel == "otaku-br" else None
        with mock.patch("scripts.build_dashboard_data.latest_research",
                        side_effect=source_for_channel):
            snapshot = make_snapshot()
        rendered = json.dumps(snapshot)
        self.assertNotIn("PRIVATE_TEST", rendered)
        self.assertNotIn("access_token=", rendered)
        self.assertIn("jojo-portal.com/en/anime/sbr/news/", rendered)

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
