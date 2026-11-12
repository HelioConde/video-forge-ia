"""No human/assistant-selected topic; agents must generate, rank, and audit."""
from __future__ import annotations
from pathlib import Path
from unittest import TestCase, main, mock

from videoforge.channel_agents.team import (
    EditorialTeamError, audit_candidates, run_team,
)

CID = "UCXGYTuBYn-0Ziqin5ajKhOw"
ROOT = Path(__file__).resolve().parents[1]


def video(idx, name, views, seconds=100):
    return {
        "id": f"abcd{idx:07d}"[-11:],
        "title": name, "duration_seconds": seconds,
        "metrics": {
            "views": views,
            "engagedViews": round(views * .5),
            "averageViewPercentage": 66,
            "averageViewDuration": seconds * .66,
            "estimatedMinutesWatched": int(views * .75),
            "likes": 14,
        },
    }


def inventory():
    videos = [
        video(1, "Jujutsu Kaisen: porque a tecnica foi criada", 900),
        video(2, "JoJo: historia da corrida", 1100),
        video(3, "Hunter x Hunter: poder oculto de Kurapika", 800),
        video(4, "Demon Slayer: Tanjiro e suas tecnicas", 900),
    ]
    return {
        "schema": "videoforge/channel-research/v1",
        "channel_id": CID, "source": "youtube-data-v3+analytics-v2",
        "read_only": True, "history_complete": True,
        "count": len(videos),
        "window": {"start": "2026-08-01", "end": "2026-11-10", "days": 90},
        "videos": videos,
    }


def proposal(idx, title, anime):
    return {
        "id": f"idea-{idx}", "channel_id": CID,
        "anime": anime, "assunto": f"analise editorial inedita {idx}",
        "abordagem": f"consequencia narrativa {idx}",
        "titulo_provisorio": title,
        "genero": "analise", "formato": "short narrado",
        "duracao_segundos": 100,
        "justificativa": "Hipotese de pesquisa a verificar",
        "fontes_a_verificar": ["fonte oficial a conferir"],
        "evidence": {"source": "own_youtube_analytics_and_public_metadata",
                     "strength": "hypothesis", "verification_required": True},
    }


def proposals():
    return [
        proposal("a", "A jornada secreta que ainda falta entender", "Dragon Ball"),
        proposal("b", "A responsabilidade de um herói após perder tudo", "One Piece"),
        proposal("c", "Por que o detetive mudou de estratégia?", "Death Note"),
    ]


class TestEditorialTeam(TestCase):
    def test_editorial_model_matches_pinned_proxy_catalog(self):
        from videoforge.channel_agents.team import select_editorial_model
        # The pinned upstream bootstrap (2026-11) lists GPT-6.1/6/5.6,
        # not the retired model names previously hardcoded in team.py.
        catalog = {"object": "list", "data": [
            {"id": "gpt-image-2"}, {"id": "gpt-6-luna"},
            {"id": "gpt-5.6-sol"}, {"id": "gpt-6.1-sol"},
        ]}
        self.assertEqual(select_editorial_model(catalog), "gpt-6.1-sol")
        self.assertEqual(select_editorial_model(
            {"data": [{"id": "gpt-5.6-terra"}]}), "gpt-5.6-terra")
        self.assertEqual(select_editorial_model(
            {"data": [{"id": "gpt-6-astra"}]}), "gpt-6-astra")

    def test_editorial_model_fails_closed_without_text_model(self):
        from videoforge.channel_agents.team import select_editorial_model
        for payload, expected in (
            ({"data": [{"id": "gpt-image-2"}, {"id": "gpt-image-1.5"}]},
             "TEAM_NO_SUPPORTED_EDITORIAL_MODEL"),
            ({"data": [{"id": "gpt-5.4"}]},
             "TEAM_NO_SUPPORTED_EDITORIAL_MODEL"),
            ({"data": "invalid"}, "TEAM_MODEL_CATALOG_INVALID"),
            ({}, "TEAM_MODEL_CATALOG_INVALID"),
        ):
            with self.subTest(expected=expected), self.assertRaisesRegex(
                    EditorialTeamError, expected):
                select_editorial_model(payload)

    def test_researcher_not_assistant_generates_all_candidates(self):
        data = inventory()
        proposed = proposals()
        trends = {"schema": "videoforge/trend-signals/v1",
                  "read_only": True, "results": []}
        with mock.patch("videoforge.channel_agents.team.propose_candidates",
                        return_value=proposed) as ideation:
            result = run_team(channel="otaku-br", snapshot=data, trends=trends,
                              client=object(), model="mock-test-model", root=ROOT)
        ideation.assert_called_once()
        self.assertEqual(result["choices_from_assistant"], 0)
        self.assertEqual(result["proxy_calls"], 1)
        self.assertEqual(result["images_generated"], 0)
        self.assertFalse(result["upload_enabled"])
        self.assertFalse(result["video_generated"])
        self.assertEqual(result["decision_authority"], "Gerente Otaku Multicena")
        self.assertTrue(result["requires_human_editorial_review"])
        self.assertIn(result["chosen_topic"]["id"], {"idea-a", "idea-b"})
        self.assertNotEqual(result["chosen_topic"]["anime"], "Death Note")
        self.assertEqual(result["deputy"]["evaluated"], 3)
        self.assertEqual(result["deputy"]["accepted"], 2)
        self.assertEqual(len(result["agent_work"]), 4)

    def test_deputy_rejects_paused_anime_and_existing_titles(self):
        d=inventory()
        rows=proposals() + [
            proposal("d", "JoJo: historia da corrida", "JoJo")
        ]
        manager={"youtube_channel_id":CID,"paused_animes":["Death Note"]}
        reservations={"schema":"videoforge/channel-topic-reservations/v1",
                      "channel_id":CID, "entries":[]}
        result=audit_candidates(proposals=rows, snapshot=d,
                                reservations=reservations, manager=manager)
        self.assertEqual(result["accepted"],2)
        self.assertEqual(result["candidates"][2]["reason"],"PAUSED_ANIME")
        self.assertEqual(result["candidates"][3]["reason"],"TEMA_PUBLICADO_OU_MUITO_PARECIDO")

    def test_cannot_claim_full_history_without_real_inventory(self):
        d=inventory()
        d["history_complete"]=False
        with self.assertRaisesRegex(EditorialTeamError,"FULL_UPLOAD_HISTORY"):
            run_team(channel="otaku-br",snapshot=d,client=object(),model="test",root=ROOT)

    def test_cannot_rank_wrong_channel_or_mock_data(self):
        d=inventory()
        d["source"]="synthetic-dryrun"
        with self.assertRaisesRegex(EditorialTeamError,"VERIFIED_YOUTUBE_DATA"):
            run_team(channel="otaku-br",snapshot=d,client=object(),model="test",root=ROOT)
        d=inventory()
        d["channel_id"]="UCwrong"
        with self.assertRaisesRegex(EditorialTeamError,"CHANNEL_ID_MISMATCH"):
            run_team(channel="otaku-br",snapshot=d,client=object(),model="test",root=ROOT)

    def test_preflight_failure_logs_only_fixed_policy_code_without_secrets(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from videoforge.channel_agents.team import main
        import os

        env = {
            "CHANNEL_IDEATION_APPROVED": "yes",
            "GITHUB_REPOSITORY": "HelioConde/video-forge-ia",
            "GITHUB_REF": "refs/heads/main",
        }
        for message, expected in (
            ("TEAM_INSUFFICIENT_VERIFIED_METRICS",
             "EDITORIAL_TEAM_BLOCKED_TEAM_INSUFFICIENT_VERIFIED_METRICS"),
            ("token=secret-WOULD-BE-DANGEROUS", "EDITORIAL_TEAM_BLOCKED_EditorialTeamError"),
        ):
            with self.subTest(message=expected):
                output = StringIO()
                with (mock.patch.dict(os.environ, env),
                      mock.patch("videoforge.channel_agents.team.channel_policy",
                                 side_effect=EditorialTeamError(message)),
                      redirect_stdout(output)):
                    status = main(["--channel", "otaku-br", "--days", "90",
                                   "--model", "auto", "--output", "fake.json"])
                self.assertEqual(status, 1)
                self.assertIn(expected, output.getvalue())
                self.assertNotIn("secret-WOULD", output.getvalue())

    def test_researcher_failures_expose_only_fixed_safe_codes(self):
        from contextlib import redirect_stdout
        from io import StringIO
        import os
        from videoforge.channel_agents.team import main
        from videoforge.channel_agents.ideation import EditorialIdeationError

        env = {
            "CHANNEL_IDEATION_APPROVED": "yes",
            "GITHUB_REPOSITORY": "HelioConde/video-forge-ia",
            "GITHUB_REF": "refs/heads/main",
        }
        for reason, expected in (
            ("EDITORIAL_PROXY_CALL_FAILED", "EDITORIAL_TEAM_BLOCKED_EDITORIAL_PROXY_CALL_FAILED"),
            ("MODEL_JSON_INVALID", "EDITORIAL_TEAM_BLOCKED_MODEL_JSON_INVALID"),
            ("EDITORIAL_CANDIDATE_COUNT_INVALID", "EDITORIAL_TEAM_BLOCKED_EDITORIAL_CANDIDATE_COUNT_INVALID"),
            ("secret=untrusted-token", "EDITORIAL_TEAM_BLOCKED_EditorialIdeationError"),
        ):
            with self.subTest(reason=expected):
                output = StringIO()
                with (mock.patch.dict(os.environ, env),
                      mock.patch("videoforge.channel_agents.team.channel_policy",
                                 side_effect=EditorialIdeationError(reason)),
                      redirect_stdout(output)):
                    status = main(["--channel", "otaku-br", "--days", "90",
                                   "--model", "auto", "--output", "fake.json"])
                self.assertEqual(status, 1)
                self.assertIn(expected, output.getvalue())
                self.assertNotIn("untrusted-token", output.getvalue())

    def test_no_topic_returned_if_deputy_blocks_all(self):
        only_paused=[proposal("x","Um novo video", "Death Note")]
        with mock.patch("videoforge.channel_agents.team.propose_candidates",
                        return_value=only_paused):
            result=run_team(channel="otaku-br", snapshot=inventory(),
                            client=object(), model="fake", root=ROOT)
        self.assertIsNone(result["chosen_topic"])
        self.assertEqual(result["status"],"no_unique_candidate")


if __name__ == "__main__":
    main()
