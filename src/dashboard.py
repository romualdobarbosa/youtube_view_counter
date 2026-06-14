"""Dashboard Streamlit: insights sobre canais de podcast brasileiros no YouTube."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    # quando importado como pacote (python -m / testes)
    from .database import get_engine
except ImportError:
    # quando executado direto: `streamlit run src/dashboard.py`
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.database import get_engine


@st.cache_data(ttl=300)
def load(query: str) -> pd.DataFrame:
    return pd.read_sql(query, get_engine())


# Rótulos amigáveis para colunas técnicas (usados em tabelas e eixos dos gráficos).
COLUMN_LABELS = {
    "name": "Canal",
    "handle": "Handle",
    "video_count": "Nº de vídeos",
    "videos": "Nº de vídeos",
    "total_views": "Views totais",
    "avg_views": "Média de views",
    "avg_engagement_rate": "Engajamento médio",
    "short_count": "Shorts",
    "long_count": "Longos",
    "video_type": "Tipo",
    "catalog_share": "% do catálogo",
    "views_share": "% das views",
    "title": "Título",
    "views": "Views",
    "engagement_rate": "Engajamento",
    "like_rate": "Taxa de likes",
    "comment_rate": "Taxa de comentários",
    "views_per_day": "Views/dia",
    "likes": "Likes",
    "comments": "Comentários",
    "favorites": "Favoritos",
    "duration_seconds": "Duração (s)",
    "category_id": "Categoria",
    "published_at": "Publicado em",
    "collected_at": "Coleta",
    "prev_collected_at": "Coleta anterior",
    "subscriber_count": "Inscritos",
    "subscriber_delta": "Δ inscritos",
    "total_views_delta": "Δ views totais",
    "views_delta": "Δ views",
    "views_per_day_delta": "Δ views/dia",
    "uploads": "Uploads",
    "weekday": "Dia (nº)",
    "dia": "Dia",
}


def table(df: pd.DataFrame) -> None:
    """Mostra um DataFrame sem o índice, sem channel_id e com rótulos amigáveis."""
    df = df.drop(columns=["channel_id"], errors="ignore").rename(columns=COLUMN_LABELS)
    st.dataframe(df, use_container_width=True, hide_index=True)


st.set_page_config(page_title="Podcasts BR no YouTube", layout="wide")
st.title("Podcasts brasileiros no YouTube — insights")

ranking = load("SELECT * FROM v_channel_ranking")
svl = load("SELECT * FROM v_short_vs_long")
latest = load("SELECT * FROM v_latest_video_metrics")
growth = load("SELECT * FROM v_channel_growth")
vgrowth = load("SELECT * FROM v_video_growth")
cadence = load("SELECT * FROM v_upload_cadence")

if ranking.empty:
    st.warning("Sem dados ainda. Rode `python -m src.main` para coletar.")
    st.stop()

# --- Ranking de canais --------------------------------------------------------
st.header("Ranking de canais")
metric = st.selectbox(
    "Ordenar por",
    ["total_views", "avg_views", "avg_engagement_rate", "video_count"],
    format_func=lambda c: COLUMN_LABELS.get(c, c),
)
ranked = ranking.sort_values(metric, ascending=False)
st.plotly_chart(
    px.bar(
        ranked,
        x="name",
        y=metric,
        title=f"Canais por {COLUMN_LABELS.get(metric, metric)}",
        labels=COLUMN_LABELS,
    ),
    use_container_width=True,
)
table(ranked)

# --- Tese: shorts verticais dominam o consumo ---------------------------------
st.header("Curtos (verticais) vs Longos (horizontais)")
st.caption(
    "Mesmo sendo conteúdo de podcast longo, os shorts costumam capturar uma fatia de "
    "views muito maior do que sua participação no catálogo."
)
if not svl.empty:
    agg = svl.groupby("video_type")[["videos", "total_views"]].sum().reset_index()
    agg["catalog_share"] = agg["videos"] / agg["videos"].sum()
    agg["views_share"] = agg["total_views"] / agg["total_views"].sum()
    comp = agg.melt(
        id_vars="video_type",
        value_vars=["catalog_share", "views_share"],
        var_name="métrica",
        value_name="proporção",
    )
    st.plotly_chart(
        px.bar(
            comp,
            x="métrica",
            y="proporção",
            color="video_type",
            barmode="group",
            title="Participação no catálogo vs participação nas views",
            labels=COLUMN_LABELS,
        ),
        use_container_width=True,
    )
    table(svl)

# --- Picos de interesse em episódios ------------------------------------------
st.header("Episódios em destaque")
tab_top, tab_spikes = st.tabs(["Top por views", "Picos (velocity)"])
with tab_top:
    top = latest.sort_values("views", ascending=False).head(20)
    st.plotly_chart(
        px.bar(top, x="title", y="views", color="video_type", title="Top 20 vídeos", labels=COLUMN_LABELS),
        use_container_width=True,
    )
    table(top[["title", "video_type", "views", "engagement_rate", "views_per_day"]])
with tab_spikes:
    if vgrowth.empty:
        st.info("Picos exigem ao menos 2 coletas. Rode `python -m src.main` novamente mais tarde.")
    else:
        spikes = vgrowth.sort_values("views_delta", ascending=False).head(20)
        st.plotly_chart(
            px.bar(spikes, x="title", y="views_delta", title="Maiores saltos de views entre coletas", labels=COLUMN_LABELS),
            use_container_width=True,
        )
        table(spikes)

# --- Crescimento de inscritos -------------------------------------------------
st.header("Crescimento de inscritos")
if growth.empty:
    st.info("Crescimento exige ao menos 2 coletas.")
else:
    st.plotly_chart(
        px.bar(
            growth.sort_values("subscriber_delta", ascending=False),
            x="name",
            y="subscriber_delta",
            title="Δ inscritos entre coletas",
            labels=COLUMN_LABELS,
        ),
        use_container_width=True,
    )
    table(growth)

# --- Cadência de upload -------------------------------------------------------
st.header("Cadência de upload")
if not cadence.empty:
    dias = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}
    cad = cadence.merge(ranking[["channel_id", "name"]], on="channel_id", how="left")
    cad["dia"] = cad["weekday"].map(dias)
    st.plotly_chart(
        px.bar(
            cad,
            x="dia",
            y="avg_views",
            color="name",
            title="Views médias por dia de publicação",
            labels=COLUMN_LABELS,
        ),
        use_container_width=True,
    )
    table(cad.drop(columns=["weekday"]))
