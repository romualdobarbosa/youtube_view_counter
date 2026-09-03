# 🏆 Quem ganhou a guerra de relevância no YouTube brasileiro na Copa do Mundo 2026?

> Pipeline de dados real: ingestão pela **YouTube Data API v3**, transformação em
> **dbt**, persistida em **DuckDB**, servida num dashboard **Streamlit**. Aplicado a
> uma pergunta datada e específica — CazéTV, GE TV, N Sports e TNT Sports Brasil,
> quem dominou a Copa 2026 e quem segurou a audiência depois que ela acabou?

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-FF694B?logo=dbt&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?logo=duckdb&logoColor=black)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

---

## A pergunta

Quatro canais brasileiros cobriram a Copa do Mundo 2026 no YouTube: **CazéTV**, **GE
TV**, **N Sports** e **TNT Sports Brasil**. Quem realmente ganhou a atenção do
público — e quem conseguiu segurar essa audiência depois que a bola parou de rolar?

**A restrição que importa**: a YouTube Data API v3 (`channels.list`) só devolve
totais **acumulados atuais** de inscritos/views — não existe endpoint público com
série histórica. Não dá pra reconstruir uma curva de inscritos retroativa. Por isso
a métrica usada aqui é **performance por vídeo publicado em 3 janelas de tempo**
(cadência, views, engajamento, share of voice), não uma curva de crescimento:

| Janela | Período |
|---|---|
| Pré-Copa | 01/05/2026 – 10/06/2026 |
| Copa | 11/06/2026 (abertura) – 19/07/2026 (final) |
| Pós-Copa | 20/07/2026 – 31/08/2026 |

## O resultado

| Canal | Share of voice (Copa) | Crescimento Copa vs Pré-Copa | Δ engajamento Pós vs Copa |
|---|---:|---:|---:|
| **CazéTV** | **94,9 %** | **+1.077 %** (11,8×) | +0,0016 |
| ge tv | 3,2 % | −54,8 % | −0,0003 |
| TNT Sports Brasil | 1,8 % | −35,3 % | −0,0062 |
| N Sports | 0,1 % | −73,3 % | +0,0020 |

**CazéTV varreu a Copa** — 94,9% de share of voice entre os 4 canais durante o
torneio, um salto de quase 12× em relação ao período pré-Copa — e **segurou a
liderança depois**: no Pós-Copa seu share subiu ainda mais (58% das views do grupo),
enquanto os concorrentes voltaram a patamares parecidos com o pré-Copa. Números
reais, gerados pelo pipeline abaixo — reproduza com os comandos na seção
["Como rodar"](#como-rodar).

<details>
<summary>Por que não usei <code>search.list</code> (como o plano original previa)</summary>

`search.list` com `publishedAfter`/`publishedBefore` custa **100 unidades por
chamada** — pra 4 canais × 3 janelas, isso rapidamente vira milhares de unidades de
cota (o limite diário padrão é 10.000). Em vez disso, a ingestão reaproveita duas
funções que **já existiam** em `src/api.py`: `get_channel_full` (resolve o canal e a
*uploads playlist* numa chamada) e uma nova `get_playlist_video_ids_since`, que pagina
a *uploads playlist* via `playlistItems.list` (**1 unidade/chamada**) e para assim
que encontra um vídeo mais antigo que o início da janela de análise — não pagina o
catálogo inteiro de canais com anos de conteúdo. `videos.list` busca estatísticas em
lotes de 50 (`get_videos_stats`, já existente). Resultado: a coleta real dos 4 canais
(~9.200 vídeos na janela) custou uma fração da cota de `search.list` pra fazer a
mesma coisa.
</details>

## Como funciona

```
YouTube Data API v3
        │  src/api.py (cliente + retry/backoff, reaproveitado)
        ▼
copa2026/ingest.py  ──▶  data/copa2026.duckdb (tabela raw copa_videos, flat)
        │
        ▼  dbt (copa2026/dbt/)
   staging: stg_copa_videos (classifica a janela Pré/Copa/Pós)
   marts:   channel_window_metrics, channel_window_comparison
        │
        ▼
src/dashboard.py (Streamlit)
```

Coleta **única e retroativa** — as 3 janelas já estão no passado, não é preciso
rodar a ingestão repetidamente. Por isso não há SCD2 aqui (isso existe na análise
secundária, ver abaixo): é uma tabela fato flat, um vídeo por linha. A fronteira de
cada janela (as datas) é regra de negócio e fica no dbt (`vars` em
`copa2026/dbt/dbt_project.yml`) — mudar as janelas não exige recoletar nada, só
`dbt run` de novo.

## Como rodar

### Local (pip)

```bash
pip install -r requirements.txt
cp .env.example .env                 # preencha YOUTUBE_API_KEY (Google Cloud Console)

python -m copa2026.ingest             # coleta os 4 canais nas 3 janelas -> data/copa2026.duckdb

pip install -r copa2026/dbt/requirements.txt
cd copa2026/dbt && dbt run && dbt test && cd ../..

streamlit run src/dashboard.py        # dashboard abre na análise da Copa 2026
```

> `copa2026/dbt/requirements.txt` fica separado do `requirements.txt` de propósito
> — ver nota em [Sobre as versões do dbt](#sobre-as-versões-do-dbt-e-por-que-são-dois-projetos-separados).

### Docker / Docker Compose

```bash
cp .env.example .env

docker compose --profile copa-ingest run --rm copa-ingest   # coleta
docker compose --profile copa-dbt run --rm copa-dbt         # staging + marts
docker compose up -d dashboard                               # http://localhost:8501
```

## Modelo de dados

```
copa_videos (raw, flat — copa2026/ingest.py)
        │
        ▼ dbt staging
stg_copa_videos (+ engagement_rate, + time_window via CASE WHEN)
        │
        ▼ dbt marts (materializados como tabela no DuckDB)
channel_window_metrics       -- canal x janela x métricas (a entrega principal)
channel_window_comparison    -- 1 linha por canal, janelas lado a lado + deltas
```

## Testes

```bash
pytest                                          # ingestão (mockada) + upserts SCD2 (análise secundária)
cd copa2026/dbt && dbt test                     # schema tests + teste de grão único (channel_id, time_window)
cd dbt && dbt test                               # análise secundária: schema tests + invariante SCD2
```

## Estrutura

```
copa2026/
├── config.py       # canais, janelas de data, caminho do DuckDB
├── ingest.py        # orquestração da coleta (reaproveita src/api.py)
└── dbt/              # staging + marts (dbt-duckdb)

src/
├── api.py           # cliente YouTube Data API v3 (compartilhado pelas 2 análises)
├── config.py         # credenciais, canais de podcast, logging
├── database.py        # modelos ORM + upserts SCD2 (análise secundária)
├── main.py             # orquestração da ingestão de podcasts
├── ranking.py            # CLI de ranking de podcasts
├── dashboard.py            # dashboard Streamlit — página padrão: Copa 2026
└── pages/
    └── 1_🎙️_Podcasts_BR.py  # página secundária: ranking de podcasts

dbt/                  # staging + marts da análise secundária (dbt-sqlite)
```

---

## Podcasts BR (segunda análise, mesmo pipeline)

O mesmo padrão — ingestão pela YouTube Data API + transformação em dbt — também
alimenta uma segunda análise, sem relação com a Copa: ranking de canais de podcast
brasileiros, com dimensões **SCD2** (histórico de atributos que mudam devagar,
como nome/handle de canal) e fatos de snapshot (métricas coletadas repetidamente ao
longo do tempo — a diferença de desenho pro caso da Copa, que é uma coleta única).
6 views analíticas (ranking, shorts vs. longos, cadência de upload, crescimento
entre coletas) viraram modelos dbt em `dbt/` (adapter `dbt-sqlite`, sobre o mesmo
`data/youtube.db`).

Acesse pela aba **Podcasts BR** do dashboard, ou:

```bash
python -m src.main                    # coleta (precisa de várias execuções ao longo do tempo)
cd dbt && dbt run && dbt test
python -m src.ranking --by views --shorts
```

Detalhes de ingestão (retry/backoff, tolerância a falha por canal), SCD2 e Docker
desse fluxo estão comentados no código (`src/database.py`, `src/main.py`,
`docker-compose.yml`, profiles `ingest`/`dbt`).

---

## Sobre as versões do dbt (e por que são dois projetos separados)

`dbt/` (podcasts, adapter `dbt-sqlite`) e `copa2026/dbt/` (Copa 2026, adapter
`dbt-duckdb`) pinam versões de `dbt-core` **diferentes e incompatíveis entre si**:

- `dbt-sqlite` não acompanha os releases recentes de `dbt-core`/`dbt-adapters` — a
  combinação "tudo na última versão" quebra o import do adaptador. A combinação
  testada e funcional (validada com `dbt run`/`dbt test` reais) está fixa em
  `dbt/requirements.txt`: `dbt-core==1.11.14` + `dbt-adapters==1.16.7` +
  `dbt-sqlite==1.10.0`. Precisa de **Python 3.11/3.12** — `dbt-common` (via
  `mashumaro`) quebra em Python 3.14.
- `dbt-duckdb` acompanha o `dbt-core` bem mais de perto — funcionou de primeira
  inclusive em Python 3.14, sem downgrade nenhum (`copa2026/dbt/requirements.txt`).

Por isso os dois `requirements.txt` de dbt ficam fora do `requirements-docker.txt`
da imagem principal: cada serviço do `docker-compose.yml` (`dbt`/`copa-dbt`) instala
as suas próprias dependências na hora de rodar, em vez de tudo pré-instalado num
único ambiente onde elas colidiriam.

## Roadmap

- [x] dbt como camada de transformação (staging + marts + testes) nas duas análises
- [x] Testes automatizados das funções de upsert SCD2 (podcasts)
- [ ] Agendar a ingestão de podcasts (cron / GitHub Actions) pra alimentar o
      histórico SCD2 automaticamente
- [ ] Expandir a análise da Copa pra outros eventos datados (eleições, Olimpíadas)
