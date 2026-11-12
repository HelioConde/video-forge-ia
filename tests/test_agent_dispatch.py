"""Tests for the private text task runner; no real Proxy calls or uploads."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from videoforge.production.agent_dispatch import (
    DispatchError, plan_text_dispatch, run_text_draft,
)
from videoforge.production.dispatcher import build_plan, mark_verified, ready_tasks
from videoforge.proxy.client import ProxyError


class StubProxy:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def chat(self, payload):
        self.calls.append(payload)
        if self.fail:
            raise ProxyError("upstream sensitive token is not public")
        return {"choices": [{"message": {"content": "Proposta revisavel, nao publicada."}}]}


class DispatchTextTests(unittest.TestCase):
    def setUp(self):
        self.plan = build_plan({
            "id": "job-001",
            "canal": "otaku-br",
            "tema": "pauta previamente validada",
            "duracao_segundos": 90,
        })
        self.env = {"VIDEOFORGE_AGENT_EXECUTION_APPROVED": "yes",
                    "VIDEOFORGE_AGENT_MODEL": "test-proxy-model"}

    def test_only_ready_text_tasks_are_planned_without_network(self):
        result = plan_text_dispatch(self.plan)
        self.assertEqual(result["mode"], "planning_only")
        self.assertEqual(result["proxy_requests_sent"], 0)
        self.assertEqual(len(result["ready_text_agents"]), 1)
        self.assertEqual(result["ready_text_agents"][0]["role_id"], "coordenador-pautas")
        self.assertEqual(result["ready_text_agents"][0]["task_id"], "briefing")
        self.assertFalse(result["publishing_enabled"])

    def test_execution_requires_dual_authorization_before_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "private"
            p = StubProxy()
            args = dict(plan=self.plan, task_id="briefing", context="Contexto editorial validado",
                        private_dir=out, client=p, model="test-proxy-model")
            with self.assertRaisesRegex(DispatchError, "NOT_AUTHORIZED"):
                run_text_draft(**args)
            with self.assertRaisesRegex(DispatchError, "NOT_AUTHORIZED"):
                run_text_draft(**args, authorized=True, env={})
            self.assertFalse(out.exists())
            self.assertEqual(p.calls, [])

    def test_one_proxy_request_creates_private_draft_no_autoapproval(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "private"
            proxy = StubProxy()
            result = run_text_draft(
                self.plan, "briefing", context="Contexto editorial validado",
                private_dir=out, authorized=True, env=self.env, client=proxy,
            )
            self.assertEqual(len(proxy.calls), 1)
            self.assertEqual(proxy.calls[0]["model"], "test-proxy-model")
            self.assertEqual(result["status"], "awaiting_independent_review")
            self.assertFalse(result["artifact_verified"])
            self.assertFalse(result["publishing_enabled"])
            draft = out / "job-001-briefing.draft.json"
            ticket = out / "job-001-briefing.ticket.json"
            self.assertTrue(draft.exists())
            self.assertTrue(ticket.exists())
            self.assertEqual(draft.stat().st_mode & 0o777, 0o600)
            self.assertEqual(out.stat().st_mode & 0o777, 0o700)
            payload = json.loads(draft.read_text(encoding="utf-8"))
            self.assertEqual(payload["role_id"], "coordenador-pautas")
            self.assertEqual(payload["provider"], "codex_proxy")
            self.assertEqual(payload["status"], "awaiting_independent_review")
            self.assertEqual(payload["content"], "Proposta revisavel, nao publicada.")
            self.assertNotIn("content", json.loads(ticket.read_text(encoding="utf-8")))
            self.assertEqual(ready_tasks(self.plan), ["briefing"])
            self.assertFalse(self.plan["execution_enabled"])
            with self.assertRaisesRegex(DispatchError, "ALREADY_RESERVED"):
                run_text_draft(
                    self.plan, "briefing", context="Outro contexto",
                    private_dir=out, authorized=True, env=self.env, client=proxy,
                )
            self.assertEqual(len(proxy.calls), 1)

    def test_dependency_gates_and_specialist_routing(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence = Path(folder) / "verified.txt"
            evidence.write_text("independent sample", encoding="utf-8")
            proxy = StubProxy()
            with self.assertRaisesRegex(DispatchError, "NOT_READY"):
                run_text_draft(
                    self.plan, "titulo", context="Roteiro ausente", private_dir=Path(folder),
                    authorized=True, env=self.env, client=proxy,
                )
            for stage in ("briefing", "pesquisa", "roteiro"):
                mark_verified(self.plan, stage, evidence_path=evidence)
            ready = {x["task_id"] for x in plan_text_dispatch(self.plan)["ready_text_agents"]}
            self.assertTrue({"titulo", "descricao", "tags", "storyboard"} <= ready)
            result = run_text_draft(
                self.plan, "titulo", context="Roteiro confirmado", private_dir=Path(folder),
                authorized=True, env=self.env, client=proxy,
            )
            self.assertEqual(result["role_id"], "titulo")
            self.assertEqual(len(proxy.calls), 1)
            self.assertEqual(proxy.calls[0]["messages"][0]["role"], "system")

    def test_image_media_human_and_publication_stages_never_use_text_gateway(self):
        with tempfile.TemporaryDirectory() as folder:
            for stage in ("thumbnail", "visuais", "narracao", "edicao",
                          "aprovacao", "publicacao"):
                with self.subTest(stage=stage):
                    with self.assertRaisesRegex(DispatchError, "NOT_TEXT_STAGE"):
                        run_text_draft(
                            self.plan, stage, context="dados",
                            private_dir=Path(folder), authorized=True,
                            env=self.env, client=StubProxy(),
                        )

    def test_rejects_role_tampering_and_invalid_plan(self):
        plan = json.loads(json.dumps(self.plan))
        plan["tasks"][0]["responsavel"] = "publicacao"
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(DispatchError, "ROLE_OR_DEPENDENCY_MISMATCH"):
                run_text_draft(plan, "briefing", context="briefing",
                               private_dir=Path(folder), authorized=True, env=self.env,
                               client=StubProxy())
        with self.assertRaisesRegex(DispatchError, "PLAN_INVALID"):
            plan_text_dispatch({"schema": "fake", "tasks": [{"id": "briefing"}]})

    def test_backend_failure_keeps_ticket_and_disables_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            proxy = StubProxy(fail=True)
            with self.assertRaisesRegex(ValueError, "AGENT_PROXY_REQUEST_FAILED"):
                run_text_draft(self.plan, "briefing", context="documento",
                               private_dir=path, authorized=True, env=self.env,
                               client=proxy)
            self.assertTrue((path / "job-001-briefing.ticket.json").is_file())
            self.assertFalse((path / "job-001-briefing.draft.json").exists())
            with self.assertRaisesRegex(DispatchError, "ALREADY_RESERVED"):
                run_text_draft(self.plan, "briefing", context="documento",
                               private_dir=path, authorized=True, env=self.env,
                               client=proxy)
            self.assertEqual(len(proxy.calls), 1)

    def test_rejects_unsafe_output_dir(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            private = base / "unsafe"
            private.mkdir(mode=0o755)
            proxy = StubProxy()
            with self.assertRaisesRegex(DispatchError, "PERMISSIONS"):
                run_text_draft(self.plan, "briefing", context="dados",
                               private_dir=private, authorized=True, env=self.env,
                               client=proxy)
            private.rmdir()
            private.symlink_to(base, target_is_directory=True)
            with self.assertRaisesRegex(DispatchError, "SYMLINK"):
                run_text_draft(self.plan, "briefing", context="dados",
                               private_dir=private, authorized=True, env=self.env,
                               client=proxy)
            self.assertEqual(proxy.calls, [])


if __name__ == "__main__":
    unittest.main()
