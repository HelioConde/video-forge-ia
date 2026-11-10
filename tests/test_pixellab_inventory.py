"""Testes de inventário PixelLab, sem rede nem geração paga."""
import unittest

from videoforge.pixellab.inventory import inspect_account, normalize_animation, emit_summary

A="123e4567-e89b-12d3-a456-426614174000"
B="123e4567-e89b-12d3-a456-426614174001"


class Fake:
    def __init__(self, listed, details):
        self.listed=listed
        self.details=details
        self.calls=[]
    def characters(self):
        self.calls.append("GET /characters")
        return {"characters": self.listed, "total": len(self.listed)}
    def character(self, cid):
        self.calls.append("GET /characters/{id}")
        return self.details[cid]


class InventoryTest(unittest.TestCase):
    def test_recognizes_existing_and_missing_directions(self):
        fake=Fake(
            [{"id": A, "name": "Alex", "state_name": "default"}],
            {A: {"status": "completed", "animation_count": 2,
                 "rotation_urls": {"south": "url", "east": "url"},
                 "animations": [{"animation_type": "walk", "directions": [
                     {"direction": "south", "frame_count": 4, "frames": ["url"]},
                     {"direction": "east", "frame_count": 4, "frames": ["url"]}]}]}}
        )
        output=inspect_account(fake)
        self.assertEqual(output["animacoes"]["existentes"]["walk"], ["east", "south"])
        self.assertNotIn("south", output["animacoes"]["faltantes"]["walk"])
        self.assertIn("north", output["animacoes"]["faltantes"]["walk"])
        self.assertEqual(fake.calls, ["GET /characters", "GET /characters/{id}"])
        text=emit_summary(output)
        self.assertNotIn(A, text)
        self.assertNotIn("url", text)

    def test_refuses_to_guess_among_multiple_characters(self):
        fake=Fake([{"id": A,"name":"Other"},{"id": B, "name":"Other2"}],
                  {A: {"animations": [], "animation_count": 0},
                   B: {"animations": [], "animation_count": 0}})
        report=inspect_account(fake)
        self.assertEqual(report["selecao"], "ambiguo")
        self.assertEqual(report["personagens_inspecionados"], 0)

    def test_anonymous_catalog_inspects_all_without_revealing_ids(self):
        fake=Fake([{"id": A, "name": "Secret One"}, {"id": B, "name": "Secret Two"}],
          {
            A: {"animations":[{"animation_type":"walk","directions":[{"direction":"south","frame_count":4,"frames":[]}]}],"status":"completed"},
            B: {"animations":[{"animation_type":"idle","directions":[{"direction":"north","frame_count":4,"frames":[]}]}],"status":"completed"},
          })
        report=inspect_account(fake)
        self.assertEqual(len(report["catalogo_anonimo"]),2)
        self.assertEqual(fake.calls.count("GET /characters/{id}"),2)
        rendered=emit_summary(report)
        self.assertNotIn(A, rendered)
        self.assertNotIn(B, rendered)
        self.assertNotIn("Secret", rendered)
        self.assertIn("walk:1", rendered)
        self.assertIn("idle:1", rendered)

    def test_explicit_id_wins(self):
        fake=Fake([{"id":A,"name":"Other"},{"id":B,"name":"Alex"}],
                  {A: {"animations": [], "animation_count":0}})
        report=inspect_account(fake, character_id=A)
        self.assertEqual(report["selecao"],"secret")
        self.assertTrue(report["animacoes"]["inspecionavel"])

    def test_no_groups_does_not_claim_missing_without_schema(self):
        data=normalize_animation({"animation_count":12})
        self.assertFalse(data["inspecionavel"])
        self.assertEqual(data["faltantes"], {})

    def test_known_empty_list_marks_missing(self):
        data=normalize_animation({"animations":[],"animation_count":0})
        self.assertEqual(len(data["faltantes"]["walk"]),8)

    def test_unknown_custom_names_not_misidentified(self):
        data=normalize_animation({"animations":[{"display_name":"running", "animation_type":"run",
              "directions":[{"direction":"south","frame_count":4,"frames":["url"]}]}]})
        self.assertEqual(data["outros_grupos"], 1)
        self.assertEqual(data["existentes"]["walk"], [])


if __name__ == "__main__":
    unittest.main()
