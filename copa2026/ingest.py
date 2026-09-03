"""Coleta única e retroativa: vídeos publicados por canal na janela de análise da
Copa 2026, com estatísticas atuais. Reaproveita o cliente da YouTube Data API já
existente em src/api.py — só adiciona a orquestração e a gravação em DuckDB.

Diferente de src/main.py: não há SCD2 aqui. É uma coleta única sobre datas fixas já
no passado, não um histórico de coletas repetidas — uma tabela flat é o modelo certo.
"""

from __future__ import annotations

from datetime import datetime, timezone

import duckdb
import pandas as pd

from src import api
from src.config import setup_logging

from . import config

COLUMNS = [
    "channel_id",
    "channel_name",
    "handle",
    "video_id",
    "title",
    "published_at",
    "duration_seconds",
    "views",
    "likes",
    "comments",
    "collected_at",
]


def _within_analysis_window(published_at: str | None) -> bool:
    if not published_at:
        return False
    published_date = datetime.fromisoformat(published_at.replace("Z", "+00:00")).date()
    return config.ANALYSIS_START <= published_date <= config.ANALYSIS_END


def run(channels: list[str] | None = None) -> None:
    logger = setup_logging()
    channels = channels or config.CHANNELS

    youtube = api.build_client()
    collected_at = datetime.now(timezone.utc).replace(tzinfo=None)
    logger.info(
        "Coletando %d canais para a janela %s a %s",
        len(channels),
        config.ANALYSIS_START,
        config.ANALYSIS_END,
    )

    rows: list[dict] = []
    ok_channels = 0
    for handle in channels:
        try:
            logger.info("Canal: %s", handle)
            ch = api.get_channel_full(youtube, handle)

            uploads = ch.get("uploads_playlist_id")
            if not uploads:
                logger.warning("  sem playlist de uploads; pulando")
                ok_channels += 1
                continue

            video_ids = api.get_playlist_video_ids_since(
                youtube, uploads, since=config.ANALYSIS_START
            )
            stats = api.get_videos_stats(youtube, video_ids)
            in_window = [v for v in stats if _within_analysis_window(v.get("published_at"))]
            logger.info(
                "  %d vídeos desde %s na uploads playlist, %d dentro da janela de análise",
                len(stats),
                config.ANALYSIS_START,
                len(in_window),
            )

            for v in in_window:
                rows.append(
                    {
                        "channel_id": ch["channel_id"],
                        "channel_name": ch.get("name"),
                        "handle": handle,
                        "video_id": v["video_id"],
                        "title": v.get("title"),
                        "published_at": v.get("published_at"),
                        "duration_seconds": v.get("duration_seconds"),
                        "views": v.get("views"),
                        "likes": v.get("likes"),
                        "comments": v.get("comments"),
                        "collected_at": collected_at,
                    }
                )
            ok_channels += 1
            logger.info("  OK — %s", ch.get("name"))
        except Exception:  # não deixa um canal derrubar a coleta inteira
            logger.exception("  falha ao coletar %s", handle)

    logger.info(
        "Coleta concluída: %d/%d canais, %d vídeos na janela de análise.",
        ok_channels,
        len(channels),
        len(rows),
    )

    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=COLUMNS)
    con = duckdb.connect(str(config.DB_PATH))
    try:
        # Coleta única: cada run substitui o dataset inteiro (não é incremental).
        con.execute("DROP TABLE IF EXISTS copa_videos")
        con.execute("CREATE TABLE copa_videos AS SELECT * FROM df")
    finally:
        con.close()


if __name__ == "__main__":
    run()
