"""Offline test of the cross-run one-shot claim, without GitHub network calls."""
import base64
import io
import json
import unittest
from urllib.error import HTTPError

from videoforge.production.attempt_claim import ClaimError, claim_one_briefing
from videoforge.production.dispatcher import build_plan


class FakeResponse:
    status = 201
    def __init__(self, value):
        self.value = json.dumps(value).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, maximum):
        return self.value[:maximum]


class FakeGitHub:
    def __init__(self):
        self.requests = []
        self.paths = set()
    def open(self, request, timeout):
        path = request.full_url.split("/contents/", 1)[-1]
        self.requests.append(request)
        if path in self.paths:
            raise HTTPError(request.full_url, 422, "duplicate", {}, io.BytesIO(b"secret body"))
        self.paths.add(path)
        return FakeResponse({"content": {"path": path}, "commit": {"sha": "a" * 40}})


class ClaimTests(unittest.TestCase):
    def setUp(self):
        self.plan = build_plan({
            "id": "otaku-topic-01", "canal": "otaku-br",
            "tema": "Um misterio original sobre One Piece ainda nao publicado",
            "duracao_segundos": 90,
        })
        self.context = {
            "status": "editorial_topic_reservation_verified",
            "channel": "otaku-br",
            "anime": "One Piece",
            "title": self.plan["demand"]["tema"],
            "angle": "Uma analise original e fundamentada",
        }
        self.env = {
            "GITHUB_REPOSITORY": "HelioConde/video-forge-ia",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_ACTOR": "HelioConde",
            "GITHUB_RUN_ATTEMPT": "1",
        }
        self.github = FakeGitHub()

    def claim(self, **changes):
        kw = {
            "plan": self.plan, "context": self.context,
            "source_run_id": "43123456789",
            "run_id": "43123459999",
            "token": "github-synthetic-test-token-123456",
            "env": self.env,
            "opener": self.github.open,
        }
        kw.update(changes)
        return claim_one_briefing(**kw)

    def test_one_create_only_commit_and_no_unencrypted_content(self):
        result = self.claim()
        self.assertEqual(result["proxy_calls_sent"], 0)
        self.assertFalse(result["upload_enabled"])
        self.assertTrue(result["path"].startswith("canal/otaku-br/editorial/tentativas/"))
        self.assertEqual(len(self.github.requests), 1)
        request = self.github.requests[0]
        self.assertEqual(request.get_method(), "PUT")
        self.assertTrue(request.get_header("Authorization").startswith("Bearer "))
        payload = json.loads(request.data)
        self.assertNotIn("sha", payload)
        self.assertEqual(payload["branch"], "main")
        decoded = json.loads(base64.b64decode(payload["content"]))
        self.assertEqual(decoded["topic_id"], "otaku-topic-01")
        self.assertNotIn(self.context["title"], request.data.decode("utf-8"))
        self.assertNotIn("content", decoded)
        self.assertFalse(decoded["model_calls_confirmed"])

    def test_repeat_across_different_workflow_run_fails_closed(self):
        self.claim()
        with self.assertRaisesRegex(ClaimError, "ALREADY_RESERVED_OR_CONFLICT"):
            self.claim(run_id="43123451111")
        self.assertEqual(len(self.github.requests), 2)
        self.assertEqual(len(self.github.paths), 1)

    def test_ref_actor_dispatch_retry_blocked_before_api(self):
        for key, value in (
            ("GITHUB_REF", "refs/heads/feature"),
            ("GITHUB_ACTOR", "unknown"),
            ("GITHUB_EVENT_NAME", "push"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_REPOSITORY", "someone/else"),
        ):
            with self.subTest(key=key):
                env = dict(self.env, **{key: value})
                with self.assertRaisesRegex(ClaimError, "RUNNER_NOT_AUTHORIZED"):
                    self.claim(env=env)
        self.assertFalse(self.github.requests)

    def test_mismatched_topic_or_publish_fails_before_api(self):
        bad = dict(self.context)
        bad["title"] = "Outro titulo nao auditado"
        with self.assertRaisesRegex(ClaimError, "UNVERIFIED_HANDOFF"):
            self.claim(context=bad)
        modified = json.loads(json.dumps(self.plan))
        modified["publishing_enabled"] = True
        with self.assertRaisesRegex(ClaimError, "UNVERIFIED_HANDOFF"):
            self.claim(plan=modified)
        self.assertEqual(self.github.requests, [])

    def test_bad_token_run_and_source_blocked(self):
        with self.assertRaisesRegex(ClaimError, "RUN_OR_TOKEN_INVALID"):
            self.claim(token="x")
        with self.assertRaisesRegex(ClaimError, "UNVERIFIED_HANDOFF"):
            self.claim(source_run_id="../../wrong")
        self.assertEqual(self.github.requests, [])


if __name__ == "__main__":
    unittest.main()
