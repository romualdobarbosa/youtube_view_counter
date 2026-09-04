"""Wrappers da YouTube Data API v3 com retry/backoff."""

from __future__ import annotations

import re
import ssl
from datetime import date, datetime
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from .config import get_api_key

_DURATION_RE = re.compile(
    r"P(?:(?P<days>\d+)D)?T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?"
)


def parse_duration(iso8601: str | None) -> int:
    """Converte uma duração ISO-8601 (ex.: 'PT1H2M3S') em segundos. None/'' -> 0."""
    if not iso8601:
        return 0
    match = _DURATION_RE.fullmatch(iso8601)
    if not match:
        return 0
    parts = {k: int(v) for k, v in match.groupdict(default="0").items()}
    return (
        parts["days"] * 86400
        + parts["hours"] * 3600
        + parts["minutes"] * 60
        + parts["seconds"]
    )


def build_client():
    """Cria o cliente da YouTube Data API v3."""
    return build("youtube", "v3", developerKey=get_api_key(), cache_discovery=False)


def _is_transient(exc: BaseException) -> bool:
    """True para erros recuperáveis: 5xx do servidor, 403 de quota transitória, e
    falhas de conexão (a mesma conexão HTTP fica ociosa entre canais — um canal
    grande pode levar dezenas de minutos só gravando no banco antes de voltar a
    chamar a API — e cai com BrokenPipeError/SSLError/timeout antes da próxima
    chamada; validado num run real contra o Turso)."""
    if isinstance(exc, (ConnectionError, ssl.SSLError, TimeoutError)):
        return True
    if not isinstance(exc, HttpError):
        return False
    status = getattr(exc.resp, "status", None)
    if status is None:
        return False
    if 500 <= int(status) < 600:
        return True
    # 403 pode ser quota transitória (rateLimitExceeded / userRateLimitExceeded);
    # quotaExceeded (diário) não adianta repetir, mas tenacity para após 5 tentativas.
    return int(status) == 403


@retry(
    retry=retry_if_exception(_is_transient),
    wait=wait_exponential(multiplier=2, min=2, max=32),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _execute(request) -> dict[str, Any]:
    """Executa uma request da API com retry exponencial para erros transitórios."""
    return request.execute()


def _safe_int(value: Any) -> int:
    """statistics podem vir ausentes (ex.: likes ocultos). Default 0."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_channel_full(youtube, handle_or_id: str) -> dict[str, Any]:
    """Busca canal por @handle ou channel ID em 1 chamada.

    Retorna dicionário com identidade, estatísticas e o id da playlist de uploads.
    """
    kwargs: dict[str, Any] = {"part": "snippet,statistics,contentDetails"}
    if handle_or_id.startswith("@"):
        kwargs["forHandle"] = handle_or_id
    elif handle_or_id.startswith("UC"):
        kwargs["id"] = handle_or_id
    else:
        kwargs["forHandle"] = "@" + handle_or_id

    resp = _execute(youtube.channels().list(**kwargs))
    items = resp.get("items", [])
    if not items:
        raise ValueError(f"Canal não encontrado: {handle_or_id!r}")
    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    content = item.get("contentDetails", {})

    return {
        "channel_id": item["id"],
        "name": snippet.get("title"),
        "handle": snippet.get("customUrl"),
        "country": snippet.get("country"),
        "channel_created_at": snippet.get("publishedAt"),
        "subscriber_count": _safe_int(stats.get("subscriberCount")),
        "total_views": _safe_int(stats.get("viewCount")),
        "video_count": _safe_int(stats.get("videoCount")),
        "uploads_playlist_id": content.get("relatedPlaylists", {}).get("uploads"),
    }


def get_playlist_video_ids(youtube, playlist_id: str) -> list[str]:
    """Pagina a playlist de uploads e retorna todos os video ids."""
    video_ids: list[str] = []
    page_token: str | None = None
    while True:
        resp = _execute(
            youtube.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=page_token,
            )
        )
        for item in resp.get("items", []):
            vid = item.get("contentDetails", {}).get("videoId")
            if vid:
                video_ids.append(vid)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return video_ids


def get_playlist_video_ids_since(
    youtube, playlist_id: str, since: date
) -> list[str]:
    """Pagina a playlist de uploads e para assim que encontrar um vídeo publicado
    antes de `since` — evita paginar o catálogo inteiro em canais com anos de
    conteúdo quando só interessa uma janela recente. Assume a ordem padrão da API
    (mais recente primeiro); se o primeiro item de uma página já for mais antigo
    que `since`, para sem coletar nada daquela página.
    """
    video_ids: list[str] = []
    page_token: str | None = None
    while True:
        resp = _execute(
            youtube.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=page_token,
            )
        )
        reached_since = False
        for item in resp.get("items", []):
            content = item.get("contentDetails", {})
            published_at = content.get("videoPublishedAt")
            if published_at and _parse_iso_date(published_at) < since:
                reached_since = True
                break
            vid = content.get("videoId")
            if vid:
                video_ids.append(vid)
        if reached_since:
            break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return video_ids


def _parse_iso_date(iso_datetime: str) -> date:
    return datetime.fromisoformat(iso_datetime.replace("Z", "+00:00")).date()


def _chunks(seq: list[str], size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def get_videos_stats(youtube, video_ids: list[str]) -> list[dict[str, Any]]:
    """Busca metadados + estatísticas dos vídeos em lotes de 50."""
    results: list[dict[str, Any]] = []
    for batch in _chunks(video_ids, 50):
        resp = _execute(
            youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(batch),
            )
        )
        for item in resp.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})
            results.append(
                {
                    "video_id": item["id"],
                    "channel_id": snippet.get("channelId"),
                    "title": snippet.get("title"),
                    "category_id": snippet.get("categoryId"),
                    "default_language": snippet.get("defaultAudioLanguage")
                    or snippet.get("defaultLanguage"),
                    "tags": snippet.get("tags") or [],
                    "published_at": snippet.get("publishedAt"),
                    "views": _safe_int(stats.get("viewCount")),
                    "likes": _safe_int(stats.get("likeCount")),
                    "comments": _safe_int(stats.get("commentCount")),
                    "favorites": _safe_int(stats.get("favoriteCount")),
                    "duration_seconds": parse_duration(content.get("duration")),
                    "definition": content.get("definition"),
                    "has_caption": content.get("caption") == "true",
                }
            )
    return results
