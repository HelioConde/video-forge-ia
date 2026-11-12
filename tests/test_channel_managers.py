"""YouTube real é mockado por contrato. Nenhum teste acessa API/OAuth."""
from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main, mock
from urllib.parse import parse_qs, urlsplit
import json

from videoforge.channel_agents.youtube import (
    YouTubeReadOnly, YouTubeReadError, duration_seconds, oauth_access_token,
)
from videoforge.channel_agents.dedup import assert_unique, DuplicateTopic
from videoforge.channel_agents.strategy import analyse_performance, select_idea
from videoforge.channel_agents.manager import build_editorial_plan, channel_policy
from videoforge.channel_agents.reserve import reserve_topic, TopicReservationError
from videoforge.channel_agents.feedback import evaluate_uploaded_video
from videoforge.channel_agents.ideation import (
    propose_candidates, EditorialIdeationError,
)

CHANNEL = "UCXGYTuBYn-0Ziqin5ajKhOw"


def sample_metrics(views=800, duration=90, pct=75):
    return {"views": views, "estimatedMinutesWatched": 1000,
            "averageViewDuration": duration*pct/100,
            "averageViewPercentage": pct, "likes": 50}


def upload(vid, title, views=800, duration=90, pct=75):
    return {"id": vid, "title": title,
            "duration_seconds": duration,
            "metrics": sample_metrics(views, duration, pct)}


def snapshot(videos):
    return {"schema": "videoforge/channel-research/v1",
            "channel_id": CHANNEL,
            "history_complete": True, "count": len(videos),
            "window": {"start": "2026-08-12", "end": "2026-11-09", "days": 90},
            "videos": videos, "source": "youtube-data-v3+analytics-v2"}


def reservations():
    return {"schema": "videoforge/channel-topic-reservations/v1",
            "channel_id": CHANNEL, "entries": []}


def candidate(title="O impacto da decisão de um herói no arco final",
              anime="One Piece", subject="decisão do herói",
              angle="consequência narrativa", seconds=90):
    return {"id": "one-piece-hero-decision", "channel_id": CHANNEL,
            "titulo_provisorio": title, "anime": anime,
            "assunto": subject, "abordagem": angle,
            "genero": "analise", "formato": "short narrado",
            "duracao_segundos": seconds,
            "evidence": {"source": "youtube_analytics_verified",
                         "strength": "documented"}}


class FakeResponse:
    def __init__(self, payload):
        self.status = 200
        self.buf = BytesIO(json.dumps(payload).encode())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, n=-1):
        return self.buf.read(n)


class FakeYouTube:
    def __init__(self, *, mismatch=False):
        self.calls = []
        self.mismatch = mismatch

    def assert_only_get(self, req):
        assert req.get_method() == "GET"

    def open(self, req, timeout):
        url = urlsplit(req.full_url)
        p = parse_qs(url.query)
        self.calls.append((url.path, p, req.get_method()))
        if url.path.endswith("/channels"):
            return FakeResponse({"items": [{
                "id": "UCwrong" if self.mismatch else CHANNEL,
                "contentDetails": {"relatedPlaylists": {"uploads": "UUverified"}},
            }]})
        if url.path.endswith("/playlistItems"):
            return FakeResponse({"items": [
                {"contentDetails": {"videoId": "ABCDE12345x"},
                 "snippet": {"title": "Naruto curiosidade"}},
                {"contentDetails": {"videoId": "FGHIJ67890y"},
                 "snippet": {"title": "One Piece teoria"}},
            ]})
        if url.path.endswith("/videos"):
            items = []
            for id in p["id"][0].split(","):
                items.append({"id": id, "snippet": {
                    "title": "Naruto curiosidade" if id.startswith("ABCDE") else "One Piece teoria",
                    "channelId": CHANNEL, "publishedAt": "2026-10-01T00:00:00Z",
                }, "contentDetails": {"duration": "PT1M30S"},
                    "status": {"privacyStatus": "public"},
                    "statistics": {"viewCount": "800"}})
            return FakeResponse({"items": items})
        if url.path.endswith("/reports") and "filters" in p:
            self.assert_only_get(req)
            if p.get("dimensions") == ["elapsedVideoTimeRatio"]:
                headers = ["elapsedVideoTimeRatio","audienceWatchRatio","relativeRetentionPerformance"]
                rows = [[.01, 1.0, .72], [.1, .81, .60],
                        [.2, .54, .45], [1.0, .2, .40]]
            else:
                headers = ["views","engagedViews","subscribersGained",
                           "averageViewDuration","averageViewPercentage"]
                rows = [[800, 520, 15, 65, 72.2]]
            return FakeResponse({"columnHeaders":[{"name": h} for h in headers],
                                 "rows":rows})
        if url.path.endswith("/reports"):
            headers = ["video", "views", "engagedViews", "subscribersGained",
                       "estimatedMinutesWatched", "averageViewDuration",
                       "averageViewPercentage", "likes"]
            return FakeResponse({
                "columnHeaders": [{"name": h} for h in headers],
                "rows": [["ABCDE12345x", 800, 520, 15, 700, 65, 72.2, 40],
                         ["FGHIJ67890y", 700, 410, 8, 650, 66, 73.3, 35]],
            })
        if url.path.endswith("/search"):
            return FakeResponse({"items": [{"id":{"videoId":"ttttt123456"},
                                           "snippet":{"title":"Uma referência pública"}}]})
        raise AssertionError("Tentativa de usar método não autorizado: " + url.path)


class YouTubeTests(TestCase):
    def test_duration_parser(self):
        self.assertEqual(duration_seconds("PT1M30S"),90)
        self.assertEqual(duration_seconds("PT2H3M4S"),7384)
        self.assertIsNone(duration_seconds("invalid"))

    def test_identity_first_and_real_metadata(self):
        fake = FakeYouTube()
        api = YouTubeReadOnly(access_token="synthetic-access-abcdefg",
                              expected_channel_id=CHANNEL, opener=fake.open)
        report = api.snapshot(days=90, end_date=date(2026,11,9))
        self.assertTrue(report["history_complete"])
        self.assertEqual(report["count"],2)
        self.assertEqual(report["videos"][0]["metrics"]["views"],800)
        self.assertEqual(report["videos"][0]["metrics"]["engagedViews"],520)
        self.assertEqual(report["videos"][0]["metrics"]["subscribersGained"],15)
        self.assertEqual(report["videos"][0]["duration_seconds"],90)
        self.assertEqual(report["window"]["start"],"2026-08-12")
        self.assertEqual([x[0] for x in fake.calls],
                         ["/youtube/v3/channels", "/youtube/v3/playlistItems",
                          "/youtube/v3/videos", "/v2/reports"])
        self.assertTrue(all(method=="GET" for _,_,method in fake.calls))
        self.assertFalse(any("synthetic-access" in str(x) for x in fake.calls))

    def test_wrong_channel_blocks_before_video_query(self):
        fake=FakeYouTube(mismatch=True)
        api=YouTubeReadOnly(access_token="synthetic-access-abcdefg",
                            expected_channel_id=CHANNEL, opener=fake.open)
        with self.assertRaisesRegex(YouTubeReadError,"MISMATCH"):
            api.snapshot()
        self.assertEqual(len(fake.calls),1)

    def test_trend_search_is_optional_and_limited(self):
        fake=FakeYouTube()
        api=YouTubeReadOnly(access_token="synthetic-access-abcdefg",
                            expected_channel_id=CHANNEL, opener=fake.open)
        result=api.trend_signals(["naruto"],max_queries=1)
        self.assertEqual(result["results"][0]["source"],
                         "youtube-data-v3/search.list")
        with self.assertRaises(ValueError):
            api.trend_signals(["Naruto","One Piece","Bleach"])

    def test_per_video_retention_uses_verified_owner_and_same_window(self):
        fake = FakeYouTube()
        api = YouTubeReadOnly(access_token="synthetic-access-abcdefg",
                              expected_channel_id=CHANNEL, opener=fake.open)
        report = api.video_retention_insights(
            "ABCDE12345x", start_date=date(2026,10,1), end_date=date(2026,11,9))
        self.assertEqual(report["status"],"observed")
        self.assertEqual(report["engaged_views"],520)
        self.assertEqual(report["metrics"]["subscribersGained"],15)
        self.assertEqual(report["engaged_view_ratio"],.65)
        self.assertEqual(report["largest_adjacent_retention_drop"]["from_ratio"],.2)
        self.assertIsNone(report["impressions_ctr"])
        self.assertIsNone(report["shorts_feed_swipe_rate"])
        self.assertTrue(all(method=="GET" for _,_,method in fake.calls))
        self.assertEqual(len(fake.calls),4)
        self.assertEqual(fake.calls[0][0],"/youtube/v3/channels")
        self.assertEqual(fake.calls[1][0],"/youtube/v3/videos")
        self.assertEqual(fake.calls[2][1]["filters"],["video==ABCDE12345x"])
        self.assertEqual(fake.calls[3][1]["dimensions"],["elapsedVideoTimeRatio"])

    def test_insights_reject_unowned_video_before_analytics(self):
        fake = FakeYouTube(mismatch=True)
        api = YouTubeReadOnly(access_token="synthetic-access-abcdefg",
                              expected_channel_id=CHANNEL, opener=fake.open)
        with self.assertRaises(YouTubeReadError):
            api.video_retention_insights(
                "ABCDE12345x",start_date=date(2026,10,1),end_date=date(2026,11,9))
        self.assertEqual(len(fake.calls),1)

    def test_refresh_requires_two_readonly_scopes(self):
        client=json.dumps({"installed":{"client_id":"abc","client_secret":"secret"}})
        token=json.dumps({"client_id":"abc","refresh_token":"secret2","scopes":[
            "https://www.googleapis.com/auth/youtube.readonly"]})
        with self.assertRaisesRegex(YouTubeReadError,"SCOPES"):
            oauth_access_token(client,token)


class EditorialTests(TestCase):
    def setUp(self):
        self.inventory=snapshot([
            upload("A","Naruto curiosidade sobre o Hokage",1200),
            upload("B","Bleach análise de personagens",1500),
            upload("C","One Piece retrospectiva do bando",2000),
            upload("D","Fullmetal Alchemist história do mundo",900,90),
        ])
        self.reservas=reservations()
        self.policy={"id":"otaku-br","youtube_channel_id":CHANNEL,
                     "paused_animes":["Death Note"]}

    def test_fails_closed_without_history(self):
        incomplete=dict(self.inventory,history_complete=False)
        with self.assertRaises(DuplicateTopic):
            assert_unique(candidate(),inventory=incomplete,reservations=self.reservas)
        with self.assertRaises(DuplicateTopic):
            select_idea(snapshot=incomplete, reservations=self.reservas,
                        candidates=[candidate()], channel_policy=self.policy)

    def test_exact_existing_video_and_reservation(self):
        duplicate=candidate(title="Naruto curiosidade sobre o Hokage")
        with self.assertRaises(DuplicateTopic):
            assert_unique(duplicate,inventory=self.inventory,reservations=self.reservas)
        self.reservas["entries"].append(candidate())
        with self.assertRaises(DuplicateTopic):
            assert_unique(candidate(),inventory=self.inventory,reservations=self.reservas)

    def test_blocks_different_channel_and_unreadable_video(self):
        item=dict(candidate(),channel_id="UCwrong")
        with self.assertRaises(DuplicateTopic):
            assert_unique(item,inventory=self.inventory,reservations=self.reservas)
        corrupted=snapshot([{"id":"X","title":"Private video"}])
        with self.assertRaises(DuplicateTopic):
            assert_unique(candidate(),inventory=corrupted,reservations=self.reservas)

    def test_duration_ranking_and_pause(self):
        performance=analyse_performance(self.inventory)
        self.assertEqual(performance["confidence"],"supported")
        self.assertEqual(performance["best_duration_bucket"],"ate-90s")
        paused=candidate(anime="Death Note",title="Um novo ângulo sobre Death Note")
        result=select_idea(snapshot=self.inventory,reservations=self.reservas,
                           candidates=[paused,candidate()],channel_policy=self.policy)
        self.assertEqual(result["status"],"proposed_for_review")
        self.assertEqual(result["selected"]["anime"],"One Piece")
        self.assertFalse(result["production_enabled"])
        self.assertTrue(any(x["reason"]=="anime_paused" for x in result["rejections"]))

    def test_manager_provides_eighteen_specialists_isolated(self):
        result=build_editorial_plan("otaku-br",snapshot=self.inventory,
                                   candidate_rows=[candidate()])
        self.assertEqual(result["status"],"awaiting_editorial_review_and_reservation")
        self.assertEqual(len(result["tasks"]),18)
        by_id={x["id"]:x for x in result["tasks"]}
        self.assertEqual(by_id["roteiro"]["executor_capability"],"responses")
        self.assertEqual(by_id["narracao"]["responsavel"],"voz")
        self.assertEqual(by_id["titulo"]["depende_de"],["roteiro"])
        self.assertFalse(result["publish_enabled"])
        self.assertTrue(all(x["channel_scope"]=="otaku-br" for x in result["tasks"]))
        self.assertEqual(channel_policy("otaku-br")["youtube_channel_id"],CHANNEL)

    def test_atomic_reservation_blocks_repeated_topic(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "reservas.json"
            path.write_text(json.dumps(self.reservas), encoding="utf-8")
            with self.assertRaises(TopicReservationError):
                reserve_topic(candidate=candidate(), inventory=self.inventory,
                              ledger_path=path, persist_approved=False)
            saved = reserve_topic(candidate=candidate(), inventory=self.inventory,
                                  ledger_path=path, persist_approved=True)
            self.assertEqual(saved["status"], "reserved")
            self.assertEqual(len(json.loads(path.read_text())["entries"]), 1)
            with self.assertRaises(DuplicateTopic):
                reserve_topic(candidate=candidate(), inventory=self.inventory,
                              ledger_path=path, persist_approved=True)

    def test_manager_prioritizes_anime_supported_by_own_channel(self):
        self.inventory = snapshot([
            upload("N1", "Naruto um conflito explicado", 7000),
            upload("N2", "Naruto historia de um personagem", 6200),
            upload("B1", "Bleach historia de um personagem", 650),
            upload("B2", "Bleach noticia curta", 550),
            upload("A1", "Fullmetal Alchemist comparativo", 800),
            upload("A2", "Dragon Ball curiosidade", 600),
        ])
        one = candidate(anime="Naruto",subject="rumos do protagonista",
                        angle="interpretação do encerramento",
                        title="As escolhas pouco comentadas do protagonista")
        two = candidate(anime="Bleach",subject="uma nova relação",
                        angle="história e significado",
                        title="Por que uma relação muda todo o arco")
        result=select_idea(snapshot=self.inventory,reservations=self.reservas,
                           candidates=[two,one],channel_policy=self.policy)
        self.assertEqual(result["selected"]["anime"],"Naruto")
        self.assertEqual(result["evidence"]["channel_signals"]["anime"]["samples"],2)

    def test_feedback_only_comparable_peers_no_causal_claim(self):
        result = evaluate_uploaded_video(self.inventory, video_id="C")
        self.assertEqual(result["status"],"observed")
        self.assertFalse(result["causal_claim"])
        self.assertTrue(result["no_repeat_topic"])
        self.assertIn(result["next_experiment"],
                      ("test_new_original_angle","test_hook_and_pacing"))
        with self.assertRaises(ValueError):
            evaluate_uploaded_video(self.inventory,video_id="not-owned-video")

    def test_shorts_feedback_prefers_engaged_views_and_early_drop(self):
        rows=[
            upload("S0","Novo tema original",1200,90,80),
            upload("S1","Outro assunto original",800,90,70),
            upload("S2","Terceiro assunto original",850,90,72),
            upload("S3","Quarto assunto original",900,90,75),
        ]
        for i,row in enumerate(rows):
            row["format"]="short"
            row["metrics"]["engagedViews"]=600 if i==0 else 400+i*20
            row["metrics"]["subscribersGained"]=12 if i==0 else 3
        info={
            "schema":"videoforge/video-insights/v1",
            "channel_id":CHANNEL,"video_id":"S0","read_only":True,
            "window":{"start":"2026-08-12","end":"2026-11-09"},
            "retention_points":[{"elapsed_ratio":.05,"audience_watch_ratio":1.0}],
            "largest_adjacent_retention_drop":{"from_ratio":.05,"to_ratio":.1,"drop":.22},
        }
        from videoforge.channel_agents.feedback import evaluate_uploaded_video
        result=evaluate_uploaded_video(snapshot(rows),video_id="S0",detailed_insights=info)
        self.assertEqual(result["status"],"observed")
        self.assertEqual(result["metric_basis"],"engagedViews")
        self.assertEqual(result["next_experiment"],"test_first_20_percent_hook")
        self.assertEqual(result["subscribers_per_1000_measured_views"],20.0)
        self.assertEqual(result["experiment_variables"],1)
        self.assertFalse(result["publication_enabled"])
        rows[1]["metrics"].pop("engagedViews")
        self.assertEqual(evaluate_uploaded_video(snapshot(rows),video_id="S0")["status"],
                         "insufficient_engaged_views")
        rows[1]["metrics"]["engagedViews"]=420
        bad=dict(info,channel_id="UCother")
        with self.assertRaises(ValueError):
            evaluate_uploaded_video(snapshot(rows),video_id="S0",detailed_insights=bad)

    def test_insufficient_metrics_does_not_pick_best(self):
        no_metrics=snapshot([{"id":"1","title":"A","metrics":None}])
        result=select_idea(snapshot=no_metrics,reservations=self.reservas,
                           candidates=[candidate()],channel_policy=self.policy)
        self.assertEqual(result["status"],"insufficient_metrics")
        self.assertIsNone(result["selected"])


class ProxyIdeationTests(TestCase):
    def test_proxy_never_called_without_explicit_authorization(self):
        class Proxy:
            def chat(self, body): raise AssertionError("CHAMADA NÃO AUTORIZADA")
        with self.assertRaises(EditorialIdeationError):
            propose_candidates(manager={"channel":"otaku-br","youtube_channel_id":CHANNEL},
                               snapshot=snapshot([]),reservations=reservations(),
                               client=Proxy(),model="test-model",authorized=False)

    @mock.patch.dict("os.environ", {"CHANNEL_IDEATION_APPROVED":"yes"})
    def test_one_call_proposes_hypothesis_not_publication(self):
        class Proxy:
            calls=0
            def chat(self, body):
                self.calls+=1
                item=candidate()
                raw={k:item[k] for k in ("id","anime","assunto","abordagem",
                    "genero","formato","titulo_provisorio","duracao_segundos")}
                return {"choices":[{"message":{"content":json.dumps({"candidates":[raw]})}}]}
        proxy=Proxy()
        ideas=propose_candidates(manager={
            "channel":"otaku-br","youtube_channel_id":CHANNEL,"paused_animes":[],
            "goal":"animes"}, snapshot=snapshot([]), reservations=reservations(),
            client=proxy,model="test-model",authorized=True)
        self.assertEqual(proxy.calls,1)
        self.assertEqual(ideas[0]["channel_id"],CHANNEL)
        self.assertTrue(ideas[0]["evidence"]["verification_required"])


if __name__ == "__main__":
    main()
