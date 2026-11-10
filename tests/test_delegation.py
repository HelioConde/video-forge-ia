import json
import tempfile
import unittest
from pathlib import Path
from videoforge.production.dispatcher import build_plan, ready_tasks, mark_verified

class DelegationTests(unittest.TestCase):
    def setUp(self):
        self.demanda={"id":"teste-001","canal":"otaku-br","tema":"curiosidades anime","duracao_segundos":90}
    def test_plan_has_order_and_specialists(self):
        out=build_plan(self.demanda)
        self.assertEqual(len(out["tasks"]),18)
        self.assertEqual(ready_tasks(out),["briefing"])
        self.assertFalse(out["publishing_enabled"])
        self.assertFalse(out["execution_enabled"])
        self.assertEqual(next(t for t in out["tasks"] if t["id"]=="titulo")["responsavel"],"titulo")
        self.assertEqual(next(t for t in out["tasks"] if t["id"]=="descricao")["responsavel"],"descricao")
    def test_parallel_tasks_after_dependencies(self):
        out=build_plan(self.demanda)
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/"evidencia.json";f.write_text('{"ok":true}')
            for slug in ["briefing","pesquisa","roteiro"]:
                mark_verified(out,slug,evidence_path=f)
            self.assertTrue({"titulo","descricao","tags","thumbnail","storyboard","narracao"}<=set(ready_tasks(out)))
    def test_missing_artifact_cannot_mark_complete(self):
        out=build_plan(self.demanda)
        with self.assertRaises(ValueError):
            mark_verified(out,"briefing",evidence_path=Path("/tmp/__missing__"))
    def test_publishing_not_allowed_in_planner(self):
        out=build_plan(self.demanda)
        with self.assertRaises(ValueError):
            mark_verified(out,"publicacao",evidence_path=Path(__file__))
    def test_rejects_unknown_channel(self):
        self.demanda["canal"]="nao-existe"
        with self.assertRaises(ValueError):
            build_plan(self.demanda)
    def test_rejects_invalid_duration(self):
        self.demanda["duracao_segundos"]=True
        with self.assertRaises(ValueError):
            build_plan(self.demanda)
if __name__=="__main__":
    unittest.main()
