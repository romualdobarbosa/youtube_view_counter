"""Materializa os marts do dbt-sqlite (views locais) como tabelas no Turso.

dbt-sqlite só grava no arquivo local (dbt/profiles.yml aponta sempre pra
../data/youtube.db, venha ele de onde vier — ver README > "Por que dois
stores"). Sem esse passo, um consumidor que lê Turso direto (DB_BACKEND=turso,
caso do dashboard no Streamlit Cloud) nunca vê os marts: eles ficam presos no
arquivo local, que morre junto com o runner do Actions ao fim de cada run.

Só faz algo quando DB_BACKEND=turso; em modo local, src/pages já lê os marts
direto de data/youtube.db (mesmo arquivo que o dbt grava ali), nada a empurrar.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `python dbt/push_marts_to_turso.py` só põe dbt/ no sys.path, não a raiz do
# repo — precisa disso pra achar o pacote `src` (mesmo padrão de sync_replica.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from sqlalchemy import create_engine

from src.config import DB_BACKEND, DB_PATH
from src.database import get_engine

# Os mesmos 6 marts que src/pages/1_🎙️_Podcasts_BR.py lê (dbt/models/marts/).
MARTS = [
    "channel_ranking",
    "short_vs_long",
    "latest_video_metrics",
    "channel_growth",
    "video_growth",
    "upload_cadence",
]

# O custo real é por round-trip de rede (statement), não por linha — mesma
# lição de src/database.py::upsert_videos_scd2_batch (ver README > "Por que
# dois stores"). chunksize baixo o bastante pra não estourar o limite de
# parâmetros por statement do SQLite/libSQL (999) mesmo no mart mais largo
# (~16 colunas em latest_video_metrics).
CHUNKSIZE = 50


def main() -> None:
    if DB_BACKEND != "turso":
        print("DB_BACKEND != turso — nada a empurrar, dashboard local já lê data/youtube.db direto.")
        return

    local = create_engine(f"sqlite:///{DB_PATH}", future=True)
    remote = get_engine()

    with local.connect() as lconn:
        for mart in MARTS:
            df = pd.read_sql(f"SELECT * FROM {mart}", lconn)
            df.to_sql(
                mart,
                remote,
                if_exists="replace",
                index=False,
                method="multi",
                chunksize=CHUNKSIZE,
            )
            print(f"  {mart}: {len(df)} linhas empurradas pro Turso")


if __name__ == "__main__":
    main()
