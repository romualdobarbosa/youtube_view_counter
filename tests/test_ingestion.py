"""Teste de integração da ingestão (main.run): API mockada, persistência real.

Não bate na YouTube Data API de verdade — troca src.api por dados fake e verifica,
por diff de contagem de linhas, que a ingestão realmente grava o que a API "retornou".
"""

from __future__ import annotations

from sqlalchemy import select

from src import main
from src.database import (
    DimChannel,
    DimVideo,
    FactChannelMetrics,
    FactVideoMetrics,
    get_session,
    init_db,
)

FAKE_CHANNEL = {
    "channel_id": "UC_TEST_1",
    "name": "Canal Teste",
    "handle": "@testchannel",
    "country": "BR",
    "channel_created_at": "2020-01-01T00:00:00Z",
    "subscriber_count": 1000,
    "total_views": 50000,
    "video_count": 2,
    "uploads_playlist_id": "PL_TEST_1",
}

FAKE_VIDEOS = [
    {
        "video_id": "vid1",
        "channel_id": "UC_TEST_1",
        "title": "Vídeo 1",
        "category_id": "22",
        "default_language": "pt",
        "tags": ["tag1"],
        "published_at": "2024-01-01T00:00:00Z",
        "views": 1000,
        "likes": 100,
        "comments": 10,
        "favorites": 0,
        "duration_seconds": 600,
        "definition": "hd",
        "has_caption": False,
    },
    {
        "video_id": "vid2",
        "channel_id": "UC_TEST_1",
        "title": "Vídeo 2 (short)",
        "category_id": "22",
        "default_language": "pt",
        "tags": [],
        "published_at": "2024-01-02T00:00:00Z",
        "views": 500,
        "likes": 50,
        "comments": 5,
        "favorites": 0,
        "duration_seconds": 30,
        "definition": "hd",
        "has_caption": True,
    },
]


def _row_counts(session) -> dict[str, int]:
    return {
        "dim_channel": len(session.scalars(select(DimChannel)).all()),
        "dim_video": len(session.scalars(select(DimVideo)).all()),
        "fact_channel_metrics": len(session.scalars(select(FactChannelMetrics)).all()),
        "fact_video_metrics": len(session.scalars(select(FactVideoMetrics)).all()),
    }


def test_ingestao_grava_dados_retornados_pela_api(monkeypatch):
    monkeypatch.setattr(main.api, "build_client", lambda: object())
    monkeypatch.setattr(main.api, "get_channel_full", lambda youtube, handle: FAKE_CHANNEL)
    monkeypatch.setattr(
        main.api, "get_playlist_video_ids", lambda youtube, playlist_id: ["vid1", "vid2"]
    )
    monkeypatch.setattr(main.api, "get_videos_stats", lambda youtube, video_ids: FAKE_VIDEOS)

    init_db()
    session = get_session()
    before = _row_counts(session)
    session.close()

    main.run(channels=["@testchannel"])

    session = get_session()
    after = _row_counts(session)

    assert before == {k: 0 for k in before}
    assert after["dim_channel"] == before["dim_channel"] + 1
    assert after["dim_video"] == before["dim_video"] + 2
    assert after["fact_channel_metrics"] == before["fact_channel_metrics"] + 1
    assert after["fact_video_metrics"] == before["fact_video_metrics"] + 2

    channel = session.scalars(select(DimChannel)).one()
    assert channel.name == "Canal Teste"

    titles = {v.title for v in session.scalars(select(DimVideo)).all()}
    assert titles == {"Vídeo 1", "Vídeo 2 (short)"}

    video_types = {v.video_id: v.video_type for v in session.scalars(select(DimVideo)).all()}
    assert video_types == {"vid1": "long", "vid2": "short"}


def test_ingestao_nao_derruba_coleta_quando_um_canal_falha(monkeypatch):
    def get_channel_full(youtube, handle):
        if handle == "@quebrado":
            raise ValueError("Canal não encontrado")
        return FAKE_CHANNEL

    monkeypatch.setattr(main.api, "build_client", lambda: object())
    monkeypatch.setattr(main.api, "get_channel_full", get_channel_full)
    monkeypatch.setattr(
        main.api, "get_playlist_video_ids", lambda youtube, playlist_id: ["vid1", "vid2"]
    )
    monkeypatch.setattr(main.api, "get_videos_stats", lambda youtube, video_ids: FAKE_VIDEOS)

    init_db()
    main.run(channels=["@quebrado", "@testchannel"])

    session = get_session()
    assert _row_counts(session)["dim_channel"] == 1
