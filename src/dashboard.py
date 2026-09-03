"""Dashboard Streamlit — página padrão: "Quem ganhou a guerra de relevância no
YouTube brasileiro durante a Copa do Mundo 2026?"

Lê as tabelas persistidas pelo dbt (copa2026/dbt/models/marts/) no
data/copa2026.duckdb. A análise secundária (ranking de podcasts BR, mesmo
pipeline aplicado a outro problema) está em src/pages/.
"""

from __future__ import annotations

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from .config import PROJECT_ROOT
except ImportError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.config import PROJECT_ROOT

DB_PATH = PROJECT_ROOT / "data" / "copa2026.duckdb"

COLUMN_LABELS = {
    "channel_name": "Canal",
    "time_window": "Janela",
    "video_count": "Nº de vídeos",
    "total_views": "Views totais",
    "avg_views": "Média de views",
    "avg_engagement_rate": "Engajamento médio",
    "share_of_voice": "Share of voice",
    "pre_copa_videos": "Vídeos (Pré-Copa)",
    "pre_copa_views": "Views (Pré-Copa)",
    "pre_copa_engagement_rate": "Engajamento (Pré-Copa)",
    "copa_videos": "Vídeos (Copa)",
    "copa_views": "Views (Copa)",
    "copa_engagement_rate": "Engajamento (Copa)",
    "copa_share_of_voice": "Share of voice (Copa)",
    "pos_copa_videos": "Vídeos (Pós-Copa)",
    "pos_copa_views": "Views (Pós-Copa)",
    "pos_copa_engagement_rate": "Engajamento (Pós-Copa)",
    "views_growth_copa_vs_pre": "Δ views (Copa vs Pré)",
    "views_growth_pct_copa_vs_pre": "% crescimento (Copa vs Pré)",
    "engagement_delta_copa_vs_pre": "Δ engajamento (Copa vs Pré)",
    "views_delta_pos_vs_copa": "Δ views (Pós vs Copa)",
    "engagement_delta_pos_vs_copa": "Δ engajamento (Pós vs Copa)",
}

WINDOW_ORDER = ["Pré-Copa", "Copa", "Pós-Copa"]


@st.cache_data(ttl=300)
def load(query: str) -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.execute(query).df()
    finally:
        con.close()


def table(df: pd.DataFrame) -> None:
    st.dataframe(
        df.drop(columns=["channel_id"], errors="ignore").rename(columns=COLUMN_LABELS),
        use_container_width=True,
        hide_index=True,
    )


st.set_page_config(page_title="Copa 2026 — guerra de relevância no YouTube", layout="wide")
st.title("Quem ganhou a guerra de relevância no YouTube brasileiro durante a Copa do Mundo 2026?")
st.caption(
    "CazéTV, GE TV, N Sports e TNT Sports Brasil — performance por vídeo em 3 janelas: "
    "Pré-Copa (01/05–10/06), Copa (11/06–19/07) e Pós-Copa (20/07–31/08)."
)

if not DB_PATH.exists():
    st.warning(
        "Sem dados ainda. Rode a coleta e a transformação:\n\n"
        "```\npython -m copa2026.ingest\ncd copa2026/dbt && dbt run && dbt test\n```"
    )
    st.stop()

with st.expander("Por que 3 janelas de publicação, e não uma curva de inscritos?"):
    st.markdown(
        "A YouTube Data API v3 (`channels.list`) só devolve totais **acumulados atuais** "
        "de inscritos e views — não existe endpoint público com série histórica. Por isso "
        "a métrica usada é **performance por vídeo publicado em cada janela** (cadência, "
        "views, engajamento, share of voice), coletada via `playlistItems.list` + "
        "`videos.list` — não via `search.list`, que custaria ~100x mais cota de API pra "
        "fazer a mesma coisa."
    )

comparison = load("SELECT * FROM channel_window_comparison")
metrics = load("SELECT * FROM channel_window_metrics")

if comparison.empty:
    st.warning(
        "Tabelas vazias. Rode `python -m copa2026.ingest` e depois `dbt run` em "
        "`copa2026/dbt/`."
    )
    st.stop()

# --- Share of voice por janela --------------------------------------------------
st.header("Share of voice: quem dominou cada janela")
metrics["time_window"] = pd.Categorical(metrics["time_window"], categories=WINDOW_ORDER, ordered=True)
st.plotly_chart(
    px.bar(
        metrics.sort_values("time_window"),
        x="channel_name",
        y="share_of_voice",
        color="time_window",
        barmode="group",
        title="% das views totais do grupo, por canal e por janela",
        labels=COLUMN_LABELS,
    ),
    use_container_width=True,
)
table(metrics.sort_values(["time_window", "total_views"], ascending=[True, False]))

# --- Quem cresceu com a Copa -----------------------------------------------------
st.header("Quem cresceu: Copa vs Pré-Copa")
growth = comparison.sort_values("views_growth_copa_vs_pre", ascending=False)
st.plotly_chart(
    px.bar(
        growth,
        x="channel_name",
        y="views_growth_copa_vs_pre",
        title="Δ views totais (Copa − Pré-Copa)",
        labels=COLUMN_LABELS,
    ),
    use_container_width=True,
)

# --- Quem reteve engajamento depois -----------------------------------------------
st.header("Quem reteve: Pós-Copa vs Copa")
retention = comparison.sort_values("engagement_delta_pos_vs_copa", ascending=False)
st.plotly_chart(
    px.bar(
        retention,
        x="channel_name",
        y="engagement_delta_pos_vs_copa",
        title="Δ engajamento médio (Pós-Copa − Copa)",
        labels=COLUMN_LABELS,
    ),
    use_container_width=True,
)

# --- Tabela comparativa completa --------------------------------------------------
st.header("Tabela comparativa completa")
table(comparison.sort_values("copa_share_of_voice", ascending=False))
