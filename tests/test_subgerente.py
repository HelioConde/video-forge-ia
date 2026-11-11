"""Subgerente: rankings somente de entregas verificadas; sem API ou custo."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from videoforge.production.subgerente import (
    RankingEvidenceError, rank_employees, _catalog,
)
from scripts.build_dashboard_data import make_snapshot

HEX_A = "a" * 64
HEX_B = "b" * 64


def event(worker: str, i: int, *, quality: int = 90, attempts: int = 1,
          collab: bool = True, improvement: bool = False,
          reviewer: str = "revisor-conteudo") -> dict:
    e = {
        "job_id": f"job-{worker}-{i}",
        "task_id": f"tarefa-{i}",
        "employee_id": worker, "channel": "otaku-br",
        "completed_date": "2026-11-11",
        "artifact_sha256": f"{i+1:064x}",
        "reviewer_id": reviewer,
        "result": "qa_approved",
        "quality": quality,
        "attempts": attempts,
        "collaboration_confirmed": collab,
        "policy_compliant": True,
    }
    if improvement:
        e["improvement"] = {
            "previous_artifact_sha256": HEX_A,
            "summary": "Corrigiu a falha do gancho com melhoria mensurável e revisão.",
            "reviewed_by": reviewer,
        }
    return e


def payload(events: list) -> dict:
    return {
        "schema": "videoforge/performance-evidence/v1",
        "source": "trusted_backend_qa",
        "period": {"start": "2026-11-01", "end": "2026-11-30"},
        "events": events,
    }


class SubmanagerTests(unittest.TestCase):
    def test_roster_counts_and_excludes_self(self):
        catalog = _catalog(Path(__file__).resolve().parents[1])
        self.assertEqual(len(catalog), 40)  # 8 visuais + 27 especialistas + 5 gerentes
        self.assertNotIn("subgerente", catalog)
        self.assertNotIn("gerente_geral", catalog)
        self.assertEqual(len([x for x in catalog.values() if x["cohort"]=="gerentes"]),5)

    def test_no_points_without_real_qa(self):
        r = rank_employees(payload([]))
        self.assertEqual(r["status"], "awaiting_verified_evidence")
        self.assertEqual(r["ranking"], [])
        self.assertEqual(len(r["unrated"]), 40)
        self.assertTrue(all(x["points"] is None for x in r["unrated"]))
        self.assertFalse(r["auto_modify_agents"])

    def test_three_verified_jobs_required(self):
        r=rank_employees(payload([event("roteirista", 1),event("roteirista", 2)]))
        self.assertEqual(r["ranking"], [])
        waiting=next(x for x in r["unrated"] if x["employee_id"]=="roteirista")
        self.assertEqual(waiting["verified_tasks"],2)
        self.assertIsNone(waiting["points"])

    def test_points_reward_quality_and_improvement_not_volume(self):
        events=[event("roteirista", i, quality=94, improvement=(i==3)) for i in range(1,4)]
        events += [event("artista", i, quality=65) for i in range(10,19)]
        ranking=rank_employees(payload(events))
        self.assertEqual(len(ranking["ranking"]),2)
        top,second=ranking["ranking"]
        self.assertEqual(top["employee_id"],"roteirista")
        self.assertEqual(top["rank"],1)
        self.assertEqual(top["verified_tasks"],3)
        self.assertAlmostEqual(top["points"], round((47+15+10+5)*3/3+20/3,1))
        self.assertEqual(second["verified_tasks"],9)
        self.assertLess(second["points"],top["points"])
        self.assertEqual(top["cohort_rank"],1)
        self.assertEqual(second["cohort_rank"],2)

    def test_corrected_delivery_lower_consistency_but_improvement_bonus(self):
        events=[event("editor",i,quality=82,attempts=2,collab=False,improvement=True)
                for i in range(1,4)]
        report=rank_employees(payload(events))
        item=report["ranking"][0]
        self.assertEqual(item["points"], 41+9+0+20+5)
        self.assertEqual(item["score_components"]["evolucao"],20)
        self.assertTrue(item["improvement_actions"])

    def test_no_self_review_or_duplicate_job_or_failed_policy(self):
        rows=[event("roteirista",1),event("roteirista",2),event("roteirista",3)]
        bad=copy.deepcopy(rows)
        bad[0]["reviewer_id"]="roteirista"
        with self.assertRaisesRegex(RankingEvidenceError,"INDEPENDENT"):
            rank_employees(payload(bad))
        bad=copy.deepcopy(rows)
        bad[1]["job_id"]=bad[0]["job_id"]
        with self.assertRaisesRegex(RankingEvidenceError,"DUPLICATED"):
            rank_employees(payload(bad))
        bad=copy.deepcopy(rows)
        bad[2]["policy_compliant"]=False
        with self.assertRaisesRegex(RankingEvidenceError,"COMPLIANCE"):
            rank_employees(payload(bad))

    def test_untrusted_source_or_invalid_reference_blocks(self):
        p=payload([event("roteirista",1)])
        p["source"]="agent_self_report"
        with self.assertRaisesRegex(RankingEvidenceError,"UNTRUSTED"):
            rank_employees(p)
        p=payload([event("roteirista",1)])
        p["events"][0]["artifact_sha256"]="not-an-artifact"
        with self.assertRaisesRegex(RankingEvidenceError,"UNVERIFIED"):
            rank_employees(p)
        p=payload([event("roteirista",1,improvement=True)])
        p["events"][0]["improvement"]["previous_artifact_sha256"]=p["events"][0]["artifact_sha256"]
        with self.assertRaisesRegex(RankingEvidenceError,"IMPROVEMENT"):
            rank_employees(p)

    def test_public_dashboard_exports_only_aggregates(self):
        report=payload([event("editor",i,improvement=True) for i in range(1,4)])
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"private-evidence.json"
            f.write_text(json.dumps(report),encoding="utf-8")
            snap=make_snapshot(performance_evidence=f)
        board=snap["ranking_funcionarios"]
        self.assertEqual(board["status"],"ready")
        self.assertEqual(board["ranking"][0]["id"],"editor")
        self.assertTrue(board["evidence_connected"])
        serialized=json.dumps(snap)
        for private in ("artifact_sha256","reviewer_id","job_id",
                        "previous_artifact_sha256","completed_date"):
            self.assertNotIn(private,serialized)


if __name__=="__main__":
    unittest.main()
