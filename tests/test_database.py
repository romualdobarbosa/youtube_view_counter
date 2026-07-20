"""Testes das funções de upsert SCD2 e inserts de fato (database.py)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from src.database import (
    DimChannel,
    DimVideo,
    FactChannelMetrics,
    FactVideoMetrics,
    get_engine,
    get_session,
    init_db,
    insert_channel_metrics,
    insert_video_metrics,
    upsert_channel_scd2,
    upsert_video_scd2,
)

CHANNEL_V1 = {
    "channel_id": "UC_TEST_1",
    "name": "Canal Teste",
    "handle": "@testchannel",
    "country": "BR",
    "channel_created_at": "2020-01-01T00:00:00Z",
}

VIDEO_V1 = {
    "video_id": "vid1",
    "channel_id": "UC_TEST_1",
    "title": "Vídeo 1",
    "category_id": "22",
    "duration_seconds": 600,
    "tags": ["tag1"],
}


def _count(session, model) -> int:
    return len(session.scalars(select(model)).all())


def test_upsert_channel_scd2_cria_linha_nova():
    init_db()
    session = get_session()
    now = datetime(2026, 1, 1)

    assert _count(session, DimChannel) == 0
    channel_key = upsert_channel_scd2(session, CHANNEL_V1, now)
    session.commit()

    assert _count(session, DimChannel) == 1
    row = session.get(DimChannel, channel_key)
    assert row.name == "Canal Teste"
    assert row.is_current is True
    assert row.valid_to is None


def test_upsert_channel_scd2_idempotente_quando_nada_muda():
    init_db()
    session = get_session()
    now = datetime(2026, 1, 1)

    key1 = upsert_channel_scd2(session, CHANNEL_V1, now)
    session.commit()
    key2 = upsert_channel_scd2(session, CHANNEL_V1, now)
    session.commit()

    assert key1 == key2
    assert _count(session, DimChannel) == 1


def test_upsert_channel_scd2_versiona_quando_nome_muda():
    init_db()
    session = get_session()
    t1 = datetime(2026, 1, 1)
    t2 = datetime(2026, 2, 1)

    key1 = upsert_channel_scd2(session, CHANNEL_V1, t1)
    session.commit()

    channel_v2 = {**CHANNEL_V1, "name": "Canal Teste Renomeado"}
    key2 = upsert_channel_scd2(session, channel_v2, t2)
    session.commit()

    assert key1 != key2
    assert _count(session, DimChannel) == 2

    old_row = session.get(DimChannel, key1)
    assert old_row.is_current is False
    assert old_row.valid_to == t2

    new_row = session.get(DimChannel, key2)
    assert new_row.is_current is True
    assert new_row.name == "Canal Teste Renomeado"
    assert new_row.valid_to is None


def test_upsert_video_scd2_versiona_quando_titulo_muda():
    init_db()
    session = get_session()
    t1 = datetime(2026, 1, 1)
    t2 = datetime(2026, 2, 1)

    key1 = upsert_video_scd2(session, VIDEO_V1, t1)
    session.commit()

    video_v2 = {**VIDEO_V1, "title": "Vídeo 1 (editado)"}
    key2 = upsert_video_scd2(session, video_v2, t2)
    session.commit()

    assert key1 != key2
    assert _count(session, DimVideo) == 2

    new_row = session.get(DimVideo, key2)
    assert new_row.title == "Vídeo 1 (editado)"
    assert new_row.video_type == "long"  # 600s > SHORT_MAX_SECONDS (180s)


def test_insert_metrics_grava_fato_de_snapshot():
    init_db()
    session = get_session()
    now = datetime(2026, 1, 1)

    channel_key = upsert_channel_scd2(session, CHANNEL_V1, now)
    insert_channel_metrics(
        session,
        channel_key,
        {**CHANNEL_V1, "subscriber_count": 1000, "total_views": 50000, "video_count": 1},
        now,
    )
    session.commit()

    assert _count(session, FactChannelMetrics) == 1
    fact = session.scalars(select(FactChannelMetrics)).first()
    assert fact.subscriber_count == 1000
    assert fact.total_views == 50000
