import json
import unittest
from pathlib import Path
from videoforge.config import load_video_config, resolve_model

ROOT = Path(__file__).resolve().parents[1]
CANAL = ROOT / "canal"
EXPECTED = {"otaku-br", "otaku-en", "gamer", "manu-kids", "alchemy-lab"}

class ChannelTests(unittest.TestCase):
    def test_five_real_channels(self):
        self.assertEqual({p.name for p in CANAL.iterdir() if p.is_dir()}, EXPECTED)

    def test_configs_are_safe_and_models_resolve(self):
        ids = set()
        for slug in EXPECTED:
            with self.subTest(slug=slug):
                cfg = json.loads((CANAL / slug / "canal.json").read_text(encoding="utf-8"))
                self.assertEqual(cfg["id"], slug)
                self.assertFalse(cfg["youtube"]["conectado"])
                self.assertFalse(cfg["youtube"]["upload_habilitado"])
                self.assertEqual(cfg["youtube"]["privacidade"], "private")
                self.assertEqual(cfg["youtube"]["feito_para_criancas"], slug == "manu-kids")
                self.assertTrue(cfg["youtube"]["channel_id"].startswith("UC"))
                self.assertNotIn(cfg["youtube"]["channel_id"], ids)
                ids.add(cfg["youtube"]["channel_id"])
                self.assertTrue((CANAL / slug / "conteudos" / "indice.json").exists())
                model = resolve_model(cfg, {}, ROOT / "modelos")
                self.assertEqual(model["id"], cfg["modelo_padrao"])

    def test_indices_are_not_execution_manifests(self):
        for slug in EXPECTED:
            idx = json.loads((CANAL / slug / "conteudos" / "indice.json").read_text(encoding="utf-8"))
            self.assertEqual(idx["canal_id"], slug)
            self.assertFalse(idx["producao_automatica_habilitada"])
            self.assertTrue(all(not p["executavel_no_videoforge"] for p in idx["manifestos_legados"]))

    def test_example_video_can_override_channel_model(self):
        cfg = load_video_config("canal/alchemy-lab/videos/teste-10s/video.json", ROOT)
        self.assertEqual(cfg["canal"]["id"], "alchemy-lab")
        self.assertEqual(cfg["modelo"]["id"], "camadas-animadas")
        alchemy = json.loads((CANAL / "alchemy-lab" / "canal.json").read_text(encoding="utf-8"))
        self.assertEqual(alchemy["modelo_padrao"], "imagem-estatica")

if __name__ == "__main__":
    unittest.main()
