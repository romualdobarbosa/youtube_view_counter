# youtube_counter

Coleta e analisa métricas da **YouTube Data API v3** para canais de **podcast brasileiros**,
persistindo num modelo dimensional em SQLite (dimensões SCD2 + fatos de snapshot) e expondo
insights via views SQL, um ranking CLI e um dashboard Streamlit.

## O que dá pra responder com os dados

- **Ranking de canais** por views totais, média, engajamento ou nº de vídeos (`v_channel_ranking`).
- **Curtos verticais vs longos horizontais**: prova que shorts capturam uma fatia de views
  desproporcional ao seu tamanho no catálogo, mesmo em canais de conteúdo longo (`v_short_vs_long`).
- **Picos de interesse por episódio**: top vídeos por views e maiores saltos de views entre
  coletas (`v_latest_video_metrics`, `v_video_growth`).
- **Crescimento de inscritos / views** entre coletas (`v_channel_growth`).
- **Cadência de upload** e desempenho por dia da semana (`v_upload_cadence`).

## Modelo de dados

```
dim_channel (SCD2) ─┐                fact_channel_metrics (snapshot)
                    ├─ chaves surrogate ──┤
dim_video   (SCD2) ─┘                fact_video_metrics   (snapshot)
```

- **Dimensões SCD2**: atributos lentos (nome/handle/país do canal; título/tipo/categoria/tags
  do vídeo) são versionados — `valid_from`/`valid_to`/`is_current` preservam o histórico.
- **Fatos de snapshot**: métricas voláteis (views, likes, inscritos) gravadas a cada coleta,
  uma linha por entidade por `collected_at`.

DDL de referência em [`esquema.sql`](esquema.sql); views em [`src/views.sql`](src/views.sql).

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env        # e preencha YOUTUBE_API_KEY
# revise a lista de canais em src/config.py (CHANNELS)

python -m src.main          # coleta e grava em data/youtube.db
python -m src.ranking       # ranking no terminal (--by, --shorts)
streamlit run src/dashboard.py
```

Rodar `python -m src.main` periodicamente acumula snapshots; análises de crescimento/picos
(`v_channel_growth`, `v_video_growth`) precisam de **pelo menos 2 coletas**.

## Requisitos

- `YOUTUBE_API_KEY` válida e egress de rede para `googleapis.com`.
- Python com as deps de `requirements.txt` (SQLAlchemy, google-api-python-client, tenacity,
  pandas, plotly, streamlit, python-dotenv).
