"""Testes sem internet, sem OAuth, sem gerações e sem uploads."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

from videoforge.proxy.client import ProxyClient, ProxyError, ENDPOINTS
from videoforge.proxy.private_state import (
    PrivateStateError, validate_private_state, stage_private_state,
)
from videoforge.proxy.roles import plan_bindings
from videoforge.production.dispatcher import build_plan


class FakeResponse:
    status = 200

    def __init__(self, data):
        self.content = io.BytesIO(data)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.content.close()

    def read(self, n=-1):
        return self.content.read(n)

    def __iter__(self):
        return iter(self.content)


class FakeBackend:
    def __init__(self):
        self.requests = []
        self.reply = b'{"ok":true}'

    def open(self, req, timeout):
        self.requests.append((req, timeout))
        return FakeResponse(self.reply)


class ProxyTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.client = ProxyClient(api_key="synthetic-tests-only-key-123456",
                                  opener=self.backend.open)

    def call(self, fn, path, method, body=None, *, anthropic=False):
        result = fn()
        self.assertEqual(result, {"ok": True})
        req, timeout = self.backend.requests[-1]
        self.assertEqual(req.full_url, "http://127.0.0.1:8080" + path)
        self.assertEqual(req.get_method(), method)
        self.assertEqual(req.get_header("Authorization"),
                         "Bearer synthetic-tests-only-key-123456")
        self.assertEqual(req.get_header("Anthropic-version") is not None, anthropic)
        if body is not None:
            self.assertEqual(json.loads(req.data), body)

    def test_all_22_routes_have_backend_contracts(self):
        self.assertEqual(len(ENDPOINTS), 22)
        self.assertEqual(ENDPOINTS["responses_websocket"], ("GET", "/v1/responses"))
        self.assertEqual(ENDPOINTS["images_edit"], ("POST", "/v1/images/edits"))
        self.assertTrue(ProxyClient.capabilities()["health_live"]["read_only"])
        self.assertFalse(ProxyClient.capabilities()["images_generate"]["read_only"])

    def test_health_live_never_needs_key(self):
        c = ProxyClient(api_key="", opener=self.backend.open)
        c.health_live()
        req, _ = self.backend.requests[-1]
        self.assertEqual(req.full_url, "http://127.0.0.1:8080/health/live")
        self.assertIsNone(req.get_header("Authorization"))
        with self.assertRaises(ProxyError):
            c.accounts()
        self.assertEqual(len(self.backend.requests), 1)

    def test_models_and_management_endpoints(self):
        self.call(self.client.health, "/health", "GET")
        self.call(self.client.models, "/v1/models", "GET")
        self.call(lambda: self.client.models(client_version="1/2"),
                  "/v1/models?client_version=1%2F2", "GET")
        self.call(lambda: self.client.model("gpt-6-astra"),
                  "/v1/models/gpt-6-astra", "GET")
        self.call(self.client.accounts, "/admin/accounts", "GET")
        self.call(self.client.device_login_start, "/admin/accounts/device-login/start", "POST", {})
        self.call(lambda: self.client.device_login_status("login-1"),
                  "/admin/accounts/device-login/login-1", "GET")
        self.call(lambda: self.client.account_delete("account-1"),
                  "/admin/accounts/account-1", "DELETE")
        self.call(lambda: self.client.account_patch("account-1", status="disabled"),
                  "/admin/accounts/account-1", "PATCH", {"status": "disabled"})
        self.call(lambda: self.client.account_usage("account-1"),
                  "/admin/accounts/account-1/usage?cached=true", "GET")
        self.call(lambda: self.client.account_refresh("account-1"),
                  "/admin/accounts/account-1/refresh", "POST", {})
        self.call(self.client.rotation_get, "/admin/rotation", "GET")
        self.call(lambda: self.client.rotation_put("sticky"),
                  "/admin/rotation", "PUT", {"strategy": "sticky"})

    def test_text_image_anthropic_methods(self):
        payload={"model":"gpt-6-astra","messages":[{"role":"user","content":"Ola"}]}
        self.call(lambda:self.client.completions(payload), "/v1/completions", "POST",payload)
        self.call(lambda:self.client.chat(payload), "/v1/chat/completions", "POST",payload)
        self.call(lambda:self.client.responses(payload), "/v1/responses", "POST",payload)
        self.call(lambda:self.client.compact(payload), "/v1/responses/compact", "POST",payload)
        self.call(lambda:self.client.images_generate(payload), "/v1/images/generations", "POST",payload)
        self.call(lambda:self.client.images_edit(payload), "/v1/images/edits", "POST",payload)
        self.call(lambda:self.client.messages(payload), "/v1/messages", "POST",payload,anthropic=True)
        self.call(lambda:self.client.count_tokens(payload), "/v1/messages/count_tokens", "POST",payload,anthropic=True)

    def test_sse_streams_and_no_creds_leak(self):
        self.backend.reply=b'event: message\ndata: {"delta":"a"}\n\ndata: [DONE]\n\n'
        items = list(self.client.chat_stream({"model":"gpt-6-astra"}))
        self.assertEqual(items,[{"event":"message","data":{"delta":"a"}}])
        req, _ = self.backend.requests[-1]
        self.assertEqual(req.get_header("Accept"),"text/event-stream")
        self.assertTrue(json.loads(req.data)["stream"])

    def test_security_invalid_endpoint_and_remote_no_tls(self):
        for host in ("http://api.example.com:8080","http://user:password@127.0.0.1:8080",
                     "http://localhost:8080/some/path", "file:///etc/passwd"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                ProxyClient(base_url=host,api_key="test-key-1234567890")
        # Conexoes remotas sao permitidas APENAS com TLS no backend.
        ProxyClient(base_url="https://proxy.example.com",api_key="test-key-1234567890")
        with self.assertRaises(ValueError):
            self.client.rotation_put("try-all-accounts")
        with self.assertRaises(ValueError):
            self.client.account_patch("x",status="banned")

    def test_provider_error_does_not_repeat_upstream_body(self):
        def fail(req,timeout):
            raise HTTPError(req.full_url,429,"secret=do-not-print",{},io.BytesIO(b"oauth secret"))
        client=ProxyClient(api_key="synthetic-tests-only-key-123456",opener=fail)
        with self.assertRaises(ProxyError) as caught:
            client.images_generate({"prompt":"test"})
        self.assertEqual(str(caught.exception),"Codex Proxy HTTP 429")
        self.assertNotIn("secret",str(caught.exception))


class PrivateStateTests(unittest.TestCase):
    def test_rejects_insecure_state(self):
        for value in ("", "[]", '{"records":[]}', '{"records":[{"token":{}}]}'):
            with self.subTest(value=value), self.assertRaises(PrivateStateError):
                validate_private_state(value)

    def test_exclusive_private_staging(self):
        raw=json.dumps({"records":[{"token":{"access_token":"mock-access","refresh_token":"mock-refresh"}}]})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"private"
            self.assertEqual(stage_private_state(raw,path),1)
            self.assertEqual(json.loads((path/"accounts.json").read_text()),json.loads(raw))
            self.assertEqual((path/"accounts.json").stat().st_mode & 0o777,0o600)
            with self.assertRaises(PrivateStateError):
                stage_private_state(raw,path)


class RoleTests(unittest.TestCase):
    def test_all_tasks_mapped_without_execution(self):
        demand={"id":"teste-001","canal":"gamer","tema":"Novidades","duracao_segundos":90}
        plan=build_plan(demand)
        result=plan_bindings(plan,reference_images=True)
        self.assertEqual(len(result["bindings"]),18)
        self.assertFalse(result["active_connection"])
        self.assertEqual(result["calls_sent"],0)
        mapped={b["task_id"]:b for b in result["bindings"]}
        self.assertEqual(mapped["roteiro"]["capability"],"responses")
        self.assertEqual(mapped["visuais"]["capability"],"images_edit")
        self.assertEqual(mapped["publicacao"]["backend"],"other_backend")
        self.assertTrue(mapped["publicacao"]["requires_approval"])
        self.assertEqual(mapped["aprovacao"]["backend"],"human")


if __name__ == "__main__":
    unittest.main()
