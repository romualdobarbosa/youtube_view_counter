"""Orquestração da ingestão: coleta a YouTube API e persiste no schema dimensional."""

from __future__ import annotations

from datetime import datetime, timezone

from . import api
from .config import CHANNELS, setup_logging
from .database import (
    get_session,
    init_db,
    insert_channel_metrics,
    insert_video_metrics,
    upsert_channel_scd2,
    upsert_video_scd2,
)


def run(channels: list[str] | None = None) -> None:
    logger = setup_logging()
    channels = channels or CHANNELS

    init_db()
    youtube = api.build_client()

    # Mesmo timestamp para todos os fatos do run -> idempotência/consistência da coleta.
    collected_at = datetime.now(timezone.utc).replace(tzinfo=None)
    logger.info("Iniciando coleta em %s para %d canais", collected_at, len(channels))

    total_videos = 0
    ok_channels = 0
    session = get_session()
    try:
        for handle in channels:
            try:
                logger.info("Canal: %s", handle)
                ch = api.get_channel_full(youtube, handle)
                channel_key = upsert_channel_scd2(session, ch, collected_at)
                insert_channel_metrics(session, channel_key, ch, collected_at)

                uploads = ch.get("uploads_playlist_id")
                if not uploads:
                    logger.warning("  sem playlist de uploads; pulando vídeos")
                    session.commit()
                    ok_channels += 1
                    continue

                video_ids = api.get_playlist_video_ids(youtube, uploads)
                stats = api.get_videos_stats(youtube, video_ids)
                logger.info("  %d vídeos", len(stats))

                for vid in stats:
                    video_key = upsert_video_scd2(session, vid, collected_at)
                    insert_video_metrics(session, video_key, vid, collected_at)

                session.commit()  # um commit por canal
                total_videos += len(stats)
                ok_channels += 1
                logger.info(
                    "  OK — %s | %s inscritos | %s views totais",
                    ch.get("name"),
                    ch.get("subscriber_count"),
                    ch.get("total_views"),
                )
            except Exception:  # não deixa um canal derrubar a coleta inteira
                session.rollback()
                logger.exception("  falha ao coletar %s", handle)
    finally:
        session.close()

    logger.info(
        "Coleta concluída: %d/%d canais, %d vídeos.",
        ok_channels,
        len(channels),
        total_videos,
    )


if __name__ == "__main__":
    run()
