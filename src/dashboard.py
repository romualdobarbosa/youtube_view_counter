"""Dashboard Streamlit: insights sobre canais de podcast brasileiros no YouTube."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from .database import get_engine


@st.cache_data(ttl=300)
def load(query: str) -> pd.DataFrame:
    return pd.read_sql(query, get_engine())


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
)
ranked = ranking.sort_values(metric, ascending=False)
st.plotly_chart(
    px.bar(ranked, x="name", y=metric, title=f"Canais por {metric}"),
    use_container_width=True,
)
st.dataframe(ranked, use_container_width=True)

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
        ),
        use_container_width=True,
    )
    st.dataframe(svl, use_container_width=True)

# --- Picos de interesse em episódios ------------------------------------------
st.header("Episódios em destaque")
tab_top, tab_spikes = st.tabs(["Top por views", "Picos (velocity)"])
with tab_top:
    top = latest.sort_values("views", ascending=False).head(20)
    st.plotly_chart(
        px.bar(top, x="title", y="views", color="video_type", title="Top 20 vídeos"),
        use_container_width=True,
    )
    st.dataframe(
        top[["title", "channel_id", "video_type", "views", "engagement_rate", "views_per_day"]],
        use_container_width=True,
    )
with tab_spikes:
    if vgrowth.empty:
        st.info("Picos exigem ao menos 2 coletas. Rode `python -m src.main` novamente mais tarde.")
    else:
        spikes = vgrowth.sort_values("views_delta", ascending=False).head(20)
        st.plotly_chart(
            px.bar(spikes, x="title", y="views_delta", title="Maiores saltos de views entre coletas"),
            use_container_width=True,
        )
        st.dataframe(spikes, use_container_width=True)

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
        ),
        use_container_width=True,
    )
    st.dataframe(growth, use_container_width=True)

# --- Cadência de upload -------------------------------------------------------
st.header("Cadência de upload")
if not cadence.empty:
    dias = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}
    cad = cadence.copy()
    cad["dia"] = cad["weekday"].map(dias)
    st.plotly_chart(
        px.bar(cad, x="dia", y="avg_views", color="channel_id", title="Views médias por dia de publicação"),
        use_container_width=True,
    )
    st.dataframe(cad, use_container_width=True)
