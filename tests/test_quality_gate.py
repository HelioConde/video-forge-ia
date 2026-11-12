"""Testes totalmente sintéticos: não executar gerador, mídia real ou YouTube."""
import copy
import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

from videoforge.production.dispatcher import build_plan, ready_tasks, attach_quality_report
from videoforge.production.quality_template import review_template
from videoforge.production.quality_gate import (
    inspect_media, load_policy, evaluate_quality, QualityEvidenceError,
)

DIGEST = "a" * 64
CHANNEL = "otaku-br"
JOB = "otaku-video-qa-001"


def evidence(*, attempt=1, channel=CHANNEL, score=92, checks=None, format="short"):
    policy = load_policy()
    return {
        "schema": "videoforge/quality-evidence/v1",
        "source": "trusted_backend_qa",
        "job_id": JOB, "channel": channel, "format": format,
        "attempt": attempt, "media_sha256": DIGEST,
        "producer_ids": ["roteirista-cenas", "ilustrador", "montagem"],
        "reviewers": {"content": "revisor-conteudo", "technical": "qa-tecnico"},
        "scores": {
            key: {"score": score, "reviewer_id": cfg["reviewer"],
                  "reason": "Revisão da entrega e comparação com o briefing."}
            for key, cfg in policy["dimensions"].items()
        },
        "checks": {key: True for key in
                   policy["required_checks"] + policy["kids_required_checks"]}
                  if checks is None else checks,
    }


def probe(_):
    return {"sha256": DIGEST, "bytes": 12345,
            "duration_seconds": 90.2, "width": 1080, "height": 1920,
            "fps": 30, "audio_stream_present": True, "video_stream_present": True}


def evaluate(data, **kwargs):
    return evaluate_quality(data, media_path=Path("/private/validated-video.mp4"),
                            job_id=JOB, channel=kwargs.pop("channel", CHANNEL),
                            expected_duration_seconds=90,
                            trusted_backend=kwargs.pop("trusted_backend", True),
                            probe=kwargs.pop("probe", probe), **kwargs)


class MediaInspectionTests(unittest.TestCase):
    def test_real_file_hash_and_ffprobe_result(self):
        result = SimpleNamespace(returncode=0, stdout=json.dumps({
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "90.22"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264",
                 "width": 1080, "height": 1920, "avg_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }))
        calls=[]
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return result
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"synthetic-test-clip" * 100)
            checked = inspect_media(video, runner=runner)
            self.assertEqual(checked["sha256"], sha256(video.read_bytes()).hexdigest())
            self.assertEqual(checked["duration_seconds"], 90.22)
            self.assertEqual(checked["fps"], 30)
            self.assertEqual(checked["width"], 1080)
            self.assertEqual(calls[0][0][0], "ffprobe")
            self.assertTrue(calls[0][1]["capture_output"])
            result.stdout = json.dumps({"format": {"duration": "90", "format_name": "mp4"},
                                        "streams": [{"codec_type": "video", "codec_name": "h264"}]})
            with self.assertRaises(QualityEvidenceError):
                inspect_media(video, runner=runner)
            with self.assertRaisesRegex(QualityEvidenceError, "UNSAFE"):
                inspect_media(Path(tmp) / "missing.mp4", runner=runner)


class QualityGateTests(unittest.TestCase):
    def test_quality_template_contains_no_fake_grades(self):
        plan = build_plan({"id": JOB, "canal": CHANNEL, "tema": "Nova análise original",
                           "duracao_segundos": 90})
        template = review_template(plan)
        self.assertEqual(template["source"],"unverified_template_only")
        self.assertEqual(template["status"],"awaiting_real_media_and_independent_qa")
        self.assertTrue(all(row["score"] is None for row in template["scores"].values()))
        self.assertTrue(all(value is None for value in template["checks"].values()))
        with self.assertRaises(QualityEvidenceError):
            evaluate(template)
        kids = build_plan({"id":"kids-video-001","canal":"manu-kids",
                           "tema":"História infantil inédita","duracao_segundos":90})
        self.assertIn("politica_infantil_verificada", review_template(kids)["checks"])

    def test_policy_weights_and_human_approval(self):
        policy = load_policy()
        self.assertAlmostEqual(sum(x["weight"] for x in policy["dimensions"].values()), 1)
        self.assertTrue(policy["publication"]["requires_human_approval"])
        self.assertFalse(policy["publication"]["auto_publish_enabled"])
        self.assertEqual(policy["max_revisions"], 2)

    def test_good_video_only_advances_to_human_approval(self):
        result = evaluate(evidence())
        self.assertEqual(result["status"], "ready_for_human_approval")
        self.assertFalse(result["automatic_upload_authorized"])
        self.assertFalse(result["costly_regeneration_authorized"])
        self.assertEqual(result["next_step"], "human_editorial_approval")
        self.assertEqual(result["weighted_score"], 92)

    def test_low_visuals_send_back_to_specialist(self):
        data=evidence()
        data["scores"]["consistencia_visual"]["score"]=62
        result=evaluate(data)
        self.assertEqual(result["status"], "rework")
        self.assertEqual(result["low_dimensions"], ["consistencia_visual"])
        self.assertEqual(result["remaining_revisions"], 2)
        self.assertNotIn("blocked_policy", result["status"])

    def test_after_two_revisions_suspend_instead_of_infinite_spending(self):
        data=evidence(attempt=3)
        data["scores"]["narracao"]["score"]=50
        decision=evaluate(data)
        self.assertEqual(decision["status"], "suspended")
        self.assertEqual(decision["remaining_revisions"], 0)
        self.assertFalse(decision["automatic_upload_authorized"])

    def test_policy_risks_never_autoretry(self):
        for check in ("historico_e_reserva_verificados", "conteudo_original",
                      "direitos_revisados", "fatos_verificados", "canal_correto"):
            with self.subTest(check=check):
                data=evidence()
                data["checks"][check]=False
                decision=evaluate(data)
                self.assertEqual(decision["status"], "blocked_policy")

    def test_kids_additional_safety_check(self):
        data=evidence(channel="manu-kids")
        data["checks"]["politica_infantil_verificada"]=False
        result=evaluate(data,channel="manu-kids")
        self.assertEqual(result["status"], "blocked_policy")

    def test_wrong_job_hash_reviewers_or_untrusted_data_rejected(self):
        cases=[]
        x=evidence();x["job_id"]="other-job";cases.append(x)
        x=evidence();x["media_sha256"]="b"*64;cases.append(x)
        x=evidence();x["producer_ids"].append("qa-tecnico");cases.append(x)
        x=evidence();del x["scores"]["roteiro_e_gancho"];cases.append(x)
        x=evidence();x["scores"]["narracao"]["reviewer_id"]="roteirista-cenas";cases.append(x)
        x=evidence();x["checks"].pop("conteudo_original");cases.append(x)
        for data in cases:
            with self.subTest(data=data.get("job_id")):
                with self.assertRaises(QualityEvidenceError):
                    evaluate(data)
        with self.assertRaisesRegex(QualityEvidenceError, "UNTRUSTED"):
            evaluate(evidence(),trusted_backend=False)

    def test_bad_media_duration_short_and_audio_proof(self):
        short = evaluate(evidence(),probe=lambda _: {**probe(None),"duration_seconds": 65})
        self.assertIn("SHORT_TOO_BRIEF_FOR_LOCAL_POLICY", short["media_errors"])
        self.assertEqual(short["status"], "rework")
        wrong = evaluate(evidence(),probe=lambda _: {**probe(None),"width": 350})
        self.assertIn("MEDIA_RESOLUTION_LOW", wrong["media_errors"])

    def test_approval_blocked_until_both_qas_and_gate_pass(self):
        plan=build_plan({"id":JOB,"canal":CHANNEL,"tema":"Novo anime e nova hipótese",
                         "duracao_segundos":90})
        self.assertEqual(plan["quality_gate"]["status"],"not_evaluated")
        self.assertNotIn("aprovacao",ready_tasks(plan))
        with self.assertRaisesRegex(ValueError,"Revisões"):
            attach_quality_report(plan,evidence(),media_path=Path("/tmp/x.mp4"),
                                  trusted_backend=True,probe=probe)
        for task in plan["tasks"]:
            if task["id"] not in {"aprovacao","publicacao"}:
                task["status"]="done"
                task["artifact_verified"]=True
        self.assertNotIn("aprovacao",ready_tasks(plan))
        outcome=attach_quality_report(plan,evidence(),media_path=Path("/tmp/x.mp4"),
                                      trusted_backend=True,probe=probe)
        self.assertEqual(outcome["status"],"ready_for_human_approval")
        self.assertIn("aprovacao",ready_tasks(plan))
        self.assertNotIn("publicacao",ready_tasks(plan))
        self.assertFalse(plan["publishing_enabled"])

    def test_rework_invalidates_visuals_and_downstream_qa(self):
        plan=build_plan({"id":JOB,"canal":CHANNEL,"tema":"Tema original",
                         "duracao_segundos":90})
        for task in plan["tasks"]:
            if task["id"] not in {"aprovacao","publicacao"}:
                task["status"]="done"
                task["artifact_verified"]=True
        data=evidence()
        data["scores"]["consistencia_visual"]["score"]=52
        result=attach_quality_report(plan,data,media_path=Path("/tmp/x.mp4"),
                                     trusted_backend=True,probe=probe)
        self.assertEqual(result["status"],"rework")
        ids={t["id"]:t for t in plan["tasks"]}
        for slug in ("visuais","animacao","edicao","qa_tecnico","qa_conteudo"):
            self.assertFalse(ids[slug]["artifact_verified"])
            self.assertIn(slug,result["rework_targets"])
        self.assertIn("visuais",ready_tasks(plan))
        self.assertNotIn("aprovacao",ready_tasks(plan))

    def test_revision_cannot_reset_counter_or_bypass_suspension(self):
        plan=build_plan({"id":JOB,"canal":CHANNEL,"tema":"Pauta autoral",
                         "duracao_segundos":90})
        for task in plan["tasks"]:
            if task["id"] not in {"aprovacao","publicacao"}:
                task["status"]="done"
                task["artifact_verified"]=True
        weak=evidence()
        weak["scores"]["roteiro_e_gancho"]["score"]=40
        first=attach_quality_report(plan,weak,media_path=Path("/tmp/x.mp4"),
                                    trusted_backend=True,probe=probe)
        self.assertEqual(first["status"],"rework")
        for task in plan["tasks"]:
            if task["id"] not in {"aprovacao","publicacao"}:
                task["status"]="done"
                task["artifact_verified"]=True
        with self.assertRaisesRegex(ValueError,"sequencialmente"):
            attach_quality_report(plan,weak,media_path=Path("/tmp/x.mp4"),
                                  trusted_backend=True,probe=probe)
        second=evidence(attempt=2)
        second["scores"]["roteiro_e_gancho"]["score"]=45
        attach_quality_report(plan,second,media_path=Path("/tmp/x.mp4"),
                              trusted_backend=True,probe=probe)
        for task in plan["tasks"]:
            if task["id"] not in {"aprovacao","publicacao"}:
                task["status"]="done"
                task["artifact_verified"]=True
        third=evidence(attempt=3)
        third["scores"]["roteiro_e_gancho"]["score"]=50
        last=attach_quality_report(plan,third,media_path=Path("/tmp/x.mp4"),
                                   trusted_backend=True,probe=probe)
        self.assertEqual(last["status"],"suspended")
        with self.assertRaisesRegex(ValueError,"reabertura"):
            attach_quality_report(plan,third,media_path=Path("/tmp/x.mp4"),
                                  trusted_backend=True,probe=probe)

    def test_policy_block_suspends_dispatcher(self):
        plan=build_plan({"id":JOB,"canal":CHANNEL,"tema":"Tema original",
                         "duracao_segundos":90})
        for task in plan["tasks"]:
            if task["id"] not in {"aprovacao","publicacao"}:
                task["status"]="done"
                task["artifact_verified"]=True
        data=evidence()
        data["checks"]["direitos_revisados"]=False
        result=attach_quality_report(plan,data,media_path=Path("/tmp/x.mp4"),
                                     trusted_backend=True,probe=probe)
        self.assertEqual(result["status"],"blocked_policy")
        self.assertEqual(ready_tasks(plan), [])


if __name__ == "__main__":
    unittest.main()
