"""Leitura de métricas reais do próprio canal — sem upload nem operações de escrita.

Scopes necessários: youtube.readonly e yt-analytics.readonly.
Contas são verificadas por channels.list(mine=true). Falhas e quota nunca
viram valores inventados. Requisições exigem credenciais explícitas em backend.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import json
import os
import re

DATA_API = "https://www.googleapis.com/youtube/v3"
ANALYTICS_API = "https://youtubeanalytics.googleapis.com/v2/reports"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = frozenset({
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
})
DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")
MAX_VIDEOS = 5000
MAX_CALLS = 180


class YouTubeReadError(RuntimeError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _parse_json(raw: bytes) -> dict:
    if len(raw) > 10_000_000:
        raise YouTubeReadError("YOUTUBE_RESPONSE_TOO_LARGE")
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        raise YouTubeReadError("YOUTUBE_INVALID_JSON") from None
    if not isinstance(data, dict):
        raise YouTubeReadError("YOUTUBE_INVALID_OBJECT")
    return data


def duration_seconds(value: str) -> int | None:
    if not isinstance(value, str):
        return None
    match = DURATION.fullmatch(value)
    if not match or not any(match.groups()):
        return None
    d, h, m, s = (int(part or 0) for part in match.groups())
    return d * 86400 + h * 3600 + m * 60 + s


def oauth_access_token(client_json: str, token_json: str, *, opener=None) -> str:
    """Renova token na memória; jamais imprime nem persiste OAuth ou access token."""
    try:
        conf = json.loads(client_json)
        token = json.loads(token_json)
        client = conf.get("installed") or conf.get("web") or {}
        expected = {client["client_id"], token["client_id"]}
        if (len(expected) != 1 or not client.get("client_secret")
                or not token.get("refresh_token")):
            raise ValueError("client mismatch")
        raw_scopes = token.get("scopes", ())
        scopes = set(raw_scopes.split()) if isinstance(raw_scopes, str) else set(raw_scopes)
        if not SCOPES <= scopes:
            raise ValueError("readonly scopes absent")
    except (ValueError, KeyError, TypeError):
        raise YouTubeReadError("YOUTUBE_OAUTH_CREDENTIALS_OR_SCOPES_INVALID") from None
    payload = urlencode({
        "client_id": client["client_id"],
        "client_secret": client["client_secret"],
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = Request(TOKEN_URL, data=payload,
                  headers={"Content-Type": "application/x-www-form-urlencoded"},
                  method="POST")
    try:
        with (opener or build_opener(_NoRedirect()).open)(req, timeout=15) as res:
            response = _parse_json(res.read(65537))
        access = response.get("access_token")
        if not isinstance(access, str) or len(access) < 10:
            raise YouTubeReadError("YOUTUBE_REFRESH_INVALID_RESPONSE")
        return access
    except (HTTPError, URLError, TimeoutError, OSError):
        raise YouTubeReadError("YOUTUBE_OAUTH_REFRESH_FAILED") from None


class YouTubeReadOnly:
    def __init__(self, *, access_token: str, expected_channel_id: str,
                 opener=None, max_calls: int = MAX_CALLS):
        if not isinstance(access_token, str) or len(access_token) < 10:
            raise YouTubeReadError("YOUTUBE_ACCESS_TOKEN_MISSING")
        if not isinstance(expected_channel_id, str) or not expected_channel_id.startswith("UC"):
            raise ValueError("ID do canal invalido")
        if not 5 <= max_calls <= 200:
            raise ValueError("Limite de API invalido")
        self.__token = access_token
        self.expected_channel_id = expected_channel_id
        self._open = opener or build_opener(_NoRedirect()).open
        self.calls = 0
        self.max_calls = max_calls
        self.history_complete = False

    def _get(self, base: str, params: dict[str, Any]) -> dict:
        self.calls += 1
        if self.calls > self.max_calls:
            raise YouTubeReadError("YOUTUBE_REQUEST_BUDGET_EXHAUSTED")
        req = Request(base + "?" + urlencode(params), method="GET",
                      headers={"Authorization": "Bearer " + self.__token,
                               "Accept": "application/json"})
        try:
            with self._open(req, timeout=20) as response:
                return _parse_json(response.read(10_000_001))
        except HTTPError as exc:
            raise YouTubeReadError("YOUTUBE_HTTP_" + str(exc.code)) from None
        except (URLError, OSError, TimeoutError):
            raise YouTubeReadError("YOUTUBE_CONNECTION_FAILED") from None

    def _data(self, resource: str, **params):
        if resource not in ("channels", "playlistItems", "videos", "search"):
            raise ValueError("API somente leitura")
        return self._get(f"{DATA_API}/{resource}", params)

    def verify_identity(self) -> str:
        data = self._data("channels", part="id,contentDetails", mine="true")
        rows = data.get("items", [])
        if len(rows) != 1 or rows[0].get("id") != self.expected_channel_id:
            raise YouTubeReadError("AUTHENTICATED_CHANNEL_MISMATCH")
        uploads = rows[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        if not isinstance(uploads, str) or not uploads:
            raise YouTubeReadError("UPLOADS_PLAYLIST_UNAVAILABLE")
        return uploads

    def _uploads(self, playlist: str) -> list[dict]:
        videos: list[dict] = []
        token = ""
        seen_pages: set[str] = set()
        while True:
            args = {"part": "snippet,contentDetails", "playlistId": playlist, "maxResults": 50}
            if token:
                args["pageToken"] = token
            data = self._data("playlistItems", **args)
            for row in data.get("items", []):
                video_id = row.get("contentDetails", {}).get("videoId")
                if not video_id:
                    raise YouTubeReadError("UNREADABLE_UPLOADS_INVENTORY")
                videos.append({
                    "id": video_id,
                    "title": row.get("snippet", {}).get("title", ""),
                })
                if len(videos) > MAX_VIDEOS:
                    raise YouTubeReadError("CHANNEL_INVENTORY_LIMIT_EXCEEDED")
            next_token = data.get("nextPageToken")
            if not next_token:
                return videos
            if next_token in seen_pages:
                raise YouTubeReadError("REPEATED_PLAYLIST_PAGE")
            seen_pages.add(next_token)
            token = next_token

    def _details(self, uploads: list[dict]) -> list[dict]:
        metadata = {item["id"]: item for item in uploads}
        for i in range(0, len(uploads), 50):
            ids = [item["id"] for item in uploads[i:i+50]]
            result = self._data("videos", part="snippet,contentDetails,statistics,status",
                                id=",".join(ids), maxResults=50)
            for video in result.get("items", []):
                video_id = video.get("id")
                if video_id not in metadata:
                    raise YouTubeReadError("UNEXPECTED_VIDEO_ID")
                snippet = video.get("snippet", {})
                if snippet.get("channelId") != self.expected_channel_id:
                    raise YouTubeReadError("VIDEO_OWNER_MISMATCH")
                metadata[video_id].update({
                    "title": snippet.get("title") or metadata[video_id]["title"],
                    "published_at": snippet.get("publishedAt"),
                    "duration_seconds": duration_seconds(
                        video.get("contentDetails", {}).get("duration")),
                    "privacy": video.get("status", {}).get("privacyStatus"),
                    "view_count_total": video.get("statistics", {}).get("viewCount"),
                })
        return list(metadata.values())

    def _analytics(self, *, start_date: date, end_date: date) -> dict[str, dict]:
        metrics = ("views,estimatedMinutesWatched,averageViewDuration,"
                   "averageViewPercentage,likes")
        rows = []
        offset = 1
        while True:
            page = self._get(ANALYTICS_API, {
                "ids": "channel==MINE",
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "metrics": metrics,
                "dimensions": "video",
                "sort": "-views",
                "maxResults": 200,
                "startIndex": offset,
            })
            headers = [head.get("name") for head in page.get("columnHeaders", [])]
            expected = ["video", *metrics.split(",")]
            if headers != expected:
                raise YouTubeReadError("YOUTUBE_ANALYTICS_SCHEMA_CHANGED")
            chunk = page.get("rows") or []
            if not isinstance(chunk, list) or len(chunk) > 200:
                raise YouTubeReadError("YOUTUBE_ANALYTICS_INVALID_ROWS")
            rows.extend(chunk)
            if len(chunk) < 200:
                break
            if len(rows) >= MAX_VIDEOS:
                raise YouTubeReadError("YOUTUBE_ANALYTICS_LIMIT_EXCEEDED")
            offset += len(chunk)
        return {row[0]: dict(zip(expected[1:], row[1:]))
                for row in rows if isinstance(row, list) and len(row) == len(expected)}

    def trend_signals(self, queries: list[str], *, max_queries: int = 2) -> dict:
        """Busca pública de referências; não infere retenção ou sucesso do canal."""
        if not 0 <= len(queries) <= max_queries <= 2:
            raise ValueError("No máximo duas pesquisas por análise")
        signals = []
        for term in queries:
            if not isinstance(term, str) or not 3 <= len(term.strip()) <= 80:
                raise ValueError("Termo de pesquisa inválido")
            data = self._data("search", part="snippet", type="video", q=term,
                              order="viewCount", maxResults=10, safeSearch="moderate")
            for row in data.get("items", []):
                video_id = row.get("id", {}).get("videoId")
                if not video_id or len(video_id) != 11:
                    continue
                snippet = row.get("snippet", {})
                signals.append({
                    "youtube_video_id": video_id,
                    "title": snippet.get("title", "")[:220],
                    "published_at": snippet.get("publishedAt"),
                    "query": term,
                    "source": "youtube-data-v3/search.list",
                    "private_channel_analytics": False,
                })
        return {"schema": "videoforge/trend-signals/v1",
                "read_only": True, "results": signals,
                "uses_external_public_metadata_only": True}

    def video_retention_insights(self, video_id: str, *,
                                 start_date: date, end_date: date) -> dict:
        """Retenção por ponto + engajamento do PRÓPRIO canal (somente leitura).

        audienceWatchRatio pode ultrapassar 1 após reassistir; não é porcentagem
        de likes, CTR nem "ficou versus pulou". Não consultar vídeos de terceiros.
        Usa filtros por vídeo único, como exige a API Analytics.
        """
        if (not isinstance(video_id, str) or len(video_id) != 11
                or not all(c.isalnum() or c in "-_" for c in video_id)):
            raise ValueError("ID de vídeo inválido")
        if not isinstance(start_date, date) or not isinstance(end_date, date) or end_date < start_date:
            raise ValueError("Janela Analytics inválida")
        self.verify_identity()
        details = self._data("videos", part="snippet", id=video_id)
        items = details.get("items", [])
        if len(items) != 1 or items[0].get("id") != video_id:
            raise YouTubeReadError("VIDEO_NOT_ACCESSIBLE_ON_CHANNEL")
        if items[0].get("snippet", {}).get("channelId") != self.expected_channel_id:
            raise YouTubeReadError("VIDEO_OWNER_MISMATCH")
        common = {"ids": "channel==MINE", "startDate": start_date.isoformat(),
                  "endDate": end_date.isoformat(), "filters": "video==" + video_id}
        overview_metrics = "views,engagedViews,subscribersGained,averageViewDuration,averageViewPercentage"
        overview = self._get(ANALYTICS_API, {**common, "metrics": overview_metrics})
        cols = [x.get("name") for x in overview.get("columnHeaders", [])]
        if cols != overview_metrics.split(","):
            raise YouTubeReadError("VIDEO_INSIGHTS_SCHEMA_MISMATCH")
        rows = overview.get("rows") or []
        if len(rows) > 1 or any(not isinstance(row, list) or len(row) != len(cols) for row in rows):
            raise YouTubeReadError("VIDEO_INSIGHTS_INVALID_ROWS")
        metrics = dict(zip(cols, rows[0])) if rows else None
        if metrics is None:
            return {"schema": "videoforge/video-insights/v1", "status": "insufficient_data",
                    "video_id": video_id, "channel_id": self.expected_channel_id,
                    "retention_points": [], "metrics": None,
                    "read_only": True, "source": "youtube-analytics-v2"}
        retain = self._get(ANALYTICS_API, {
            **common, "dimensions": "elapsedVideoTimeRatio",
            "metrics": "audienceWatchRatio,relativeRetentionPerformance",
            "sort": "elapsedVideoTimeRatio",
        })
        headers = [c.get("name") for c in retain.get("columnHeaders", [])]
        if headers != ["elapsedVideoTimeRatio", "audienceWatchRatio", "relativeRetentionPerformance"]:
            raise YouTubeReadError("RETENTION_SCHEMA_MISMATCH")
        points = []
        for row in retain.get("rows", []) or []:
            if not isinstance(row, list) or len(row) != 3:
                raise YouTubeReadError("RETENTION_ROW_INVALID")
            try:
                elapsed, watch, relative = map(float, row)
            except (TypeError, ValueError):
                raise YouTubeReadError("RETENTION_ROW_INVALID") from None
            if not (0 <= elapsed <= 1 and 0 <= watch <= 20 and 0 <= relative <= 1):
                raise YouTubeReadError("RETENTION_VALUES_INVALID")
            if points and elapsed <= points[-1]["elapsed_ratio"]:
                raise YouTubeReadError("RETENTION_POINTS_NOT_SORTED")
            points.append({"elapsed_ratio": elapsed, "audience_watch_ratio": watch,
                           "relative_retention": relative})
            if len(points) > 100:
                raise YouTubeReadError("RETENTION_TOO_MANY_POINTS")
        # Calcular maior queda entre amostras, sem afirmar causalidade.
        drops = [
            {"from_ratio": a["elapsed_ratio"], "to_ratio": b["elapsed_ratio"],
             "drop": round(a["audience_watch_ratio"] - b["audience_watch_ratio"], 4)}
            for a, b in zip(points, points[1:])
        ]
        largest = max(drops, key=lambda x: x["drop"]) if drops else None
        engaged = metrics.get("engagedViews")
        views = metrics.get("views")
        if not isinstance(engaged, (int,float)) or isinstance(engaged, bool) or engaged < 0:
            raise YouTubeReadError("ENGAGED_VIEWS_INVALID")
        if not isinstance(views, (int,float)) or isinstance(views, bool) or views < 0:
            raise YouTubeReadError("VIDEO_VIEWS_INVALID")
        return {
            "schema": "videoforge/video-insights/v1",
            "status": "observed" if points else "retention_unavailable",
            "video_id": video_id, "channel_id": self.expected_channel_id,
            "window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "metrics": metrics, "retention_points": points,
            "largest_adjacent_retention_drop": largest,
            "engaged_views": engaged,
            "views": views,
            "engaged_view_ratio": round(engaged / views, 4) if views else None,
            "shorts_feed_swipe_rate": None,
            "impressions_ctr": None,
            "data_comparability": "same_window_only_no_causal_inference",
            "read_only": True, "source": "youtube-analytics-v2",
        }

    def snapshot(self, *, days: int = 90, end_date: date | None = None) -> dict:
        """Coleta histórico de uploads + desempenho recente. SEM cache fictício."""
        if not 7 <= days <= 365:
            raise ValueError("Janela deve estar entre 7 e 365 dias")
        cutoff = end_date or (date.today() - timedelta(days=2))
        start = cutoff - timedelta(days=days-1)
        playlist = self.verify_identity()  # primeiro confirma canal autenticado
        uploads = self._uploads(playlist)
        videos = self._details(uploads)
        analytics = self._analytics(start_date=start, end_date=cutoff)
        for video in videos:
            video["metrics"] = analytics.get(video["id"])
        self.history_complete = True
        return {
            "schema": "videoforge/channel-research/v1",
            "channel_id": self.expected_channel_id,
            "window": {"start": start.isoformat(), "end": cutoff.isoformat(), "days": days},
            "history_complete": True,
            "count": len(videos),
            "videos": videos,
            "data_api_calls": self.calls,
            "source": "youtube-data-v3+analytics-v2",
            "read_only": True,
        }
