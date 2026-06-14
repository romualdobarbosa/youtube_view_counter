"""Ranking de canais a partir das views analíticas (CLI)."""

from __future__ import annotations

import argparse

import pandas as pd

from .database import get_engine


def channel_ranking() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM v_channel_ranking", get_engine())


def short_vs_long() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM v_short_vs_long", get_engine())


def main() -> None:
    parser = argparse.ArgumentParser(description="Ranking de canais de podcast.")
    parser.add_argument(
        "--by",
        choices=["total_views", "avg_views", "avg_engagement_rate", "video_count"],
        default="total_views",
        help="Métrica de ordenação.",
    )
    parser.add_argument("--shorts", action="store_true", help="Mostra split short vs long.")
    args = parser.parse_args()

    if args.shorts:
        df = short_vs_long()
        print(df.to_string(index=False))
        return

    df = channel_ranking().sort_values(args.by, ascending=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
