"""Verificações offline do diagnóstico sem consumir créditos."""
import unittest

from videoforge.pixellab.client import PixelLabError
from videoforge.pixellab.probe import verify_connection


class FakeClient:
    calls = []

    def __init__(self, token):
        assert token == "fake-secret"
        self.calls = []

    def _request(self, method, path):
        self.calls.append((method, path))
        if method != "GET" or path != "/balance":
            raise AssertionError("Apenas leitura autorizada")
        return {"credits": {"type": "usd", "usd": 0.50}}

    def characters(self):
        self.calls.append(("GET", "/characters"))
        return {"characters": [], "total": 0}


class ProbeTests(unittest.TestCase):
    def test_missing_token_never_connects(self):
        self.assertEqual(
            verify_connection("  ", client_factory=lambda token: self.fail("Não chamar API")),
            "NOT_CONFIGURED",
        )

    def test_read_only_connection_succeeds(self):
        fake = FakeClient("fake-secret")
        status = verify_connection("fake-secret", client_factory=lambda token: fake)
        self.assertEqual(status, "CONNECTED")
        self.assertEqual(fake.calls, [("GET", "/balance"), ("GET", "/characters")])

    def test_invalid_token_reported_without_exposing_token(self):
        class Rejected(FakeClient):
            def _request(self, method, path):
                raise PixelLabError("HTTP 401: Token PixelLab inválido.")
        self.assertEqual(verify_connection("fake-secret", client_factory=Rejected), "UNAUTHORIZED")

    def test_unexpected_response_does_not_claim_success(self):
        class Unexpected(FakeClient):
            def characters(self):
                return {"unknown": True}
        self.assertEqual(
            verify_connection("fake-secret", client_factory=Unexpected),
            "UNEXPECTED_LIBRARY_RESPONSE",
        )


if __name__ == "__main__":
    unittest.main()
