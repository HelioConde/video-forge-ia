"""Offline contract tests; never connect to Codex Proxy or spend quota."""
from __future__ import annotations

import unittest

from videoforge.proxy.agent_gateway import (
    AgentGatewayError,
    agent_proxy_catalog,
    invoke_agent,
    registered_agents,
)
from videoforge.proxy.client import ProxyError


class StubProxy:
    def __init__(self, answer=None):
        self.payloads = []
        self.answer = answer if answer is not None else {
            "choices": [{"message": {"content": "Entrega textual revisavel."}}]
        }

    def chat(self, payload):
        self.payloads.append(payload)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


class AgentGatewayTests(unittest.TestCase):
    def test_roster_is_source_of_truth_for_all_agent_roles(self):
        roles = registered_agents()
        self.assertEqual(len(roles), 36)
        self.assertEqual(len([r for r in roles.values() if r["group"] == "visual"]), 9)
        self.assertEqual(len([r for r in roles.values() if r["group"] == "specialist"]), 27)
        for role in roles.values():
            self.assertEqual(role["model_backend"], "codex_proxy")
            self.assertFalse(role["autonomous_worker_enabled"])
        catalog = agent_proxy_catalog()
        self.assertEqual(catalog["real_calls_sent"], 0)
        self.assertEqual(catalog["connection_status"], "not_checked")

    def test_default_is_closed_even_with_live_client(self):
        proxy = StubProxy()
        with self.assertRaisesRegex(AgentGatewayError, "NOT_AUTHORIZED"):
            invoke_agent(role_id="titulo", task="Criar titulo", context="Video teste",
                         client=proxy, model="model-test")
        with self.assertRaisesRegex(AgentGatewayError, "NOT_AUTHORIZED"):
            invoke_agent(role_id="titulo", task="Criar titulo", context="Video teste",
                         client=proxy, model="model-test", authorized=True)
        self.assertEqual(proxy.payloads, [])

    def test_authorized_role_can_use_shared_proxy_once_without_publishing(self):
        proxy = StubProxy()
        result = invoke_agent(
            role_id="subgerente", task="Revisar estrategia", context="Relatorio verificado",
            model="example-model", authorized=True, client=proxy,
            env={"VIDEOFORGE_AGENT_EXECUTION_APPROVED": "yes"},
        )
        self.assertEqual(len(proxy.payloads), 1)
        self.assertEqual(result["provider"], "codex_proxy")
        self.assertEqual(result["proxy_requests_sent"], 1)
        self.assertEqual(result["content"], "Entrega textual revisavel.")
        self.assertTrue(result["requires_independent_review"])
        self.assertFalse(result["video_uploaded"])
        self.assertFalse(result["autonomous_worker_activated"])
        payload = proxy.payloads[0]
        self.assertEqual(payload["model"], "example-model")
        self.assertEqual([m["role"] for m in payload["messages"]], ["system", "user"])
        self.assertNotIn("tools", payload)

    def test_role_specific_model_override(self):
        proxy = StubProxy()
        invoke_agent(
            role_id="roteirista", task="Criar estrutura", context="Briefing",
            authorized=True, client=proxy,
            env={"VIDEOFORGE_AGENT_EXECUTION_APPROVED": "yes",
                 "VIDEOFORGE_MODEL_ROTEIRISTA": "test-script-model",
                 "VIDEOFORGE_AGENT_MODEL": "test-fallback"},
        )
        self.assertEqual(proxy.payloads[0]["model"], "test-script-model")

    def test_invalid_role_model_context_rejected_before_call(self):
        proxy = StubProxy()
        common = {
            "task": "Criar titulo", "context": "Resumo",
            "authorized": True, "client": proxy,
            "env": {"VIDEOFORGE_AGENT_EXECUTION_APPROVED": "yes"},
        }
        with self.assertRaisesRegex(AgentGatewayError, "NOT_REGISTERED"):
            invoke_agent(role_id="inventado", model="example-model", **common)
        with self.assertRaisesRegex(AgentGatewayError, "NOT_CONFIGURED"):
            invoke_agent(role_id="titulo", **common)
        with self.assertRaisesRegex(AgentGatewayError, "NOT_CONFIGURED"):
            invoke_agent(role_id="titulo", model="invalid model with spaces", **common)
        with self.assertRaisesRegex(AgentGatewayError, "CONTEXT_INVALID"):
            invoke_agent(role_id="titulo", model="example-model", context="x" * 16001,
                         task="Criar titulo", authorized=True, client=proxy,
                         env=common["env"])
        self.assertEqual(proxy.payloads, [])

    def test_upstream_failure_and_invalid_response_fail_closed(self):
        env = {"VIDEOFORGE_AGENT_EXECUTION_APPROVED": "yes"}
        args = {
            "role_id": "titulo", "task": "Criar titulo",
            "context": "Briefing", "model": "example-model",
            "authorized": True, "env": env,
        }
        with self.assertRaisesRegex(AgentGatewayError, "REQUEST_FAILED"):
            invoke_agent(client=StubProxy(ProxyError("private upstream details")), **args)
        with self.assertRaisesRegex(AgentGatewayError, "REPLY_INVALID"):
            invoke_agent(client=StubProxy({"choices": []}), **args)


if __name__ == "__main__":
    unittest.main()
