# 📊 YouTube View Counter

> Pipeline de dados que coleta métricas da **YouTube Data API v3** para canais de podcast
> brasileiros, modela tudo num **data warehouse dimensional** (dimensões SCD2 + fatos de
> snapshot) em SQLite e entrega insights via **views SQL**, uma **CLI de ranking** e um
> **dashboard Streamlit**.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

---

## Por que este projeto

Um caso de ponta a ponta de **engenharia de dados analíticos**: ingestão resiliente a partir
de uma API pública, modelagem dimensional com **historização SCD2**, separação entre dimensões
e fatos, e uma camada semântica de views que transforma dados brutos em respostas de negócio.

**Demonstra:** modelagem dimensional (Kimball) · SCD Tipo 2 · ingestão idempotente com
retry/backoff · SQL analítico (CTEs, window functions) · visualização · código limpo e tipado.

## Destaques técnicos

- **SCD2 de verdade**: atributos que mudam devagar (nome/handle/país do canal; título/tipo/
  categoria/tags do vídeo) são **versionados** com `valid_from` / `valid_to` / `is_current` —
  dá pra reconstruir "como era" em qualquer ponto do tempo. Métricas voláteis (views, likes,
  inscritos) ficam em **tabelas-fato de snapshot**, uma linha por entidade por coleta.
- **Ingestão resiliente**: resolução de `@handle` ou `UCxxxx` numa única chamada, paginação,
  retry com backoff (`tenacity`), e tolerância a falhas — um canal inválido é logado e pulado,
  sem derrubar a coleta dos demais.
- **Camada semântica**: 6 views SQL encapsulam as regras de análise, mantendo o dashboard e a
  CLI livres de SQL frágil.

## O que dá pra responder com os dados

| Pergunta | View |
|---|---|
| Ranking de canais por views / média / engajamento / nº de vídeos | `v_channel_ranking` |
| Shorts capturam views desproporcionais ao tamanho do catálogo? | `v_short_vs_long` |
| Quais episódios bombaram e quais tiveram maior salto entre coletas? | `v_latest_video_metrics`, `v_video_growth` |
| Quanto o canal cresceu (inscritos/views) entre coletas? | `v_channel_growth` |
| Qual a cadência de upload e o melhor dia da semana pra publicar? | `v_upload_cadence` |

## Modelo de dados

```
dim_channel (SCD2) ─┐                        ┌─ fact_channel_metrics (snapshot)
                    ├── chaves surrogate ────┤
dim_video   (SCD2) ─┘                        └─ fact_video_metrics   (snapshot)
```

- **Dimensões SCD2**: histórico preservado via `valid_from` / `valid_to` / `is_current`.
- **Fatos de snapshot**: métricas gravadas a cada execução, ligadas à versão vigente da dimensão.

DDL de referência em [`esquema.sql`](esquema.sql); definição das views em
[`src/views.sql`](src/views.sql).

## Estrutura

```
src/
├── config.py      # canais monitorados, caminhos, credenciais, logging
├── api.py         # cliente da YouTube Data API + parsing/normalização
├── database.py    # modelos ORM, upserts SCD2, inserts de fato
├── main.py        # orquestração da ingestão
├── views.sql      # camada semântica (6 views analíticas)
├── ranking.py     # ranking no terminal
└── dashboard.py   # dashboard Streamlit
```

## Como rodar

### Via pip (ambiente local)

```bash
pip install -r requirements.txt
cp .env.example .env          # preencha YOUTUBE_API_KEY (Google Cloud Console)
# revise a lista de canais em src/config.py (CHANNELS)

python -m src.main            # coleta e grava em data/youtube.db
python -m src.ranking --by views --shorts
streamlit run src/dashboard.py
```

### Via Docker / Docker Compose

```bash
cp .env.example .env          # preencha YOUTUBE_API_KEY (Google Cloud Console)

docker compose up -d dashboard              # sobe o dashboard em http://localhost:8501
docker compose --profile ingest run --rm ingest   # roda a ingestão sob demanda
```

- `dashboard` é o único serviço que sobe por padrão (`docker compose up`) — ele só lê
  `data/youtube.db`, nunca chama a API do YouTube.
- `ingest` fica atrás do profile `ingest` de propósito: assim `docker compose up` nunca
  consome cota da API sem você pedir explicitamente.
- Os dois serviços compartilham `./data` e `./logs` via bind mount, então uma coleta feita
  pelo `ingest` fica disponível para o `dashboard` imediatamente (o dashboard cacheia por
  5 min — veja `@st.cache_data(ttl=300)` em `dashboard.py`).
- Em distros com SELinux enforcing (Fedora, RHEL, CentOS) os volumes já usam a flag `:z`
  no `docker-compose.yml`, necessária para o container conseguir escrever nos bind mounts.
- A imagem usa `requirements-docker.txt` (subconjunto enxuto de `requirements.txt`, só com
  as libs de runtime) para não carregar Jupyter/notebook/etc. — bagagem de ambiente de dev
  que não pertence à imagem de produção.

> 💡 Rodar a ingestão periodicamente (`python -m src.main` local ou
> `docker compose --profile ingest run --rm ingest`) acumula snapshots. As análises de
> crescimento e de picos (`v_channel_growth`, `v_video_growth`) precisam de **pelo menos
> 2 coletas**.

## Stack

`Python` · `SQLAlchemy 2.0` · `SQLite` · `google-api-python-client` · `tenacity` · `pandas` ·
`plotly` · `Streamlit` · `python-dotenv` · `Docker` / `Docker Compose`

## Roadmap

- [ ] Agendar a ingestão (cron / GitHub Actions) para alimentar o histórico SCD2 automaticamente
- [ ] Testes automatizados das funções de upsert SCD2
- [ ] Exportar as views para um modelo de BI (dbt / Metabase)
