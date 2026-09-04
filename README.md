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

| Janela   | Período                                    |
| -------- | ------------------------------------------ |
| Pré-Copa | 01/05/2026 – 10/06/2026                    |
| Copa     | 11/06/2026 (abertura) – 19/07/2026 (final) |
| Pós-Copa | 20/07/2026 – 31/08/2026                    |

## O resultado

| Canal             | Share of voice (Copa) | Crescimento Copa vs Pré-Copa | Δ engajamento Pós vs Copa |
| ----------------- | --------------------: | ---------------------------: | ------------------------: |
| **CazéTV**        |            **94,9 %** |         **+1.077 %** (11,8×) |                   +0,0016 |
| ge tv             |                 3,2 % |                      −54,8 % |                   −0,0003 |
| TNT Sports Brasil |                 1,8 % |                      −35,3 % |                   −0,0062 |
| N Sports          |                 0,1 % |                      −73,3 % |                   +0,0020 |

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
_uploads playlist_ numa chamada) e uma nova `get_playlist_video_ids_since`, que pagina
a _uploads playlist_ via `playlistItems.list` (**1 unidade/chamada**) e para assim
que encontra um vídeo mais antigo que o início da janela de análise — não pagina o
catálogo inteiro de canais com anos de conteúdo. `videos.list` busca estatísticas em
lotes de 50 (`get_videos_stats`, já existente). Resultado: a coleta real dos 4 canais
(~9.200 vídeos na janela) custou uma fração da cota de `search.list` pra fazer a
mesma coisa.

</details>

## Escopo e limitações (o que este número é e o que não é)

O 94,9% é **share of views entre 4 canais brasileiros de esporte no
YouTube** — não é a fatia da CazéTV na audiência total da Copa. Duas
fronteiras importam:

**1. O universo é o YouTube, não a Copa.** A verdadeira concorrência da
CazéTV era a TV aberta (Globo, SBT). A GE TV, inclusive, concentrou a
audiência digital dela no Globoplay — fora deste recorte. Então o número
mede "quem dominou o YouTube entre quem apostou no YouTube", não "quem
dominou a Copa". A CazéTV tinha os direitos integrais dos 104 jogos na
plataforma; o resultado reflete essa aposta, não repercussão geral.

**2. Medir o impacto real esbarra em fontes fechadas.** Responder "a
CazéTV incomodou/superou a TV tradicional?" exigiria cruzar três tipos de
dado heterogêneos, e a ingestão de dois deles é o gargalo real:

| Fonte                           | O que traria                  | Por que fica de fora                                                                                                          |
| ------------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| YouTube Data API                | Views/engajamento (grão fino) | ✅ já ingerido aqui                                                                                                           |
| Ibope / Kantar                  | Audiência de TV aberta        | Proprietário, sem API — só números soltos na imprensa, em unidade incompatível (pontos da Grande SP × dispositivos nacionais) |
| Social listening (X, Instagram) | Buzz / menções                | APIs pagas/travadas; T1melens e Comscore usaram ferramenta paga (Brandwatch)                                                  |

Por isso este projeto responde **uma pergunta que os dados sustentam de
ponta a ponta** ("quem venceu no YouTube?") em vez de forçar um "índice de
relevância" unificado a partir de métricas que não são comparáveis entre si.

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
├── sync_replica.py     # Turso -> data/youtube.db local (dbt-sqlite só lê arquivo local)
└── ...

.github/workflows/
└── podcasts-ingest.yml # cron diário: ingestão -> Turso -> dbt run/test
```

---

## Podcasts BR (segunda análise, mesmo pipeline)

O mesmo padrão — ingestão pela YouTube Data API + transformação em dbt — também
alimenta uma segunda análise, sem relação com a Copa: ranking de canais de podcast
brasileiros, com dimensões **SCD2** (histórico de atributos que mudam devagar,
como nome/handle de canal) e fatos de snapshot (métricas coletadas repetidamente ao
longo do tempo — a diferença de desenho pro caso da Copa, que é uma coleta única).
6 views analíticas (ranking, shorts vs. longos, cadência de upload, crescimento
entre coletas) viraram modelos dbt em `dbt/` (adapter `dbt-sqlite`).

**5 canais** (os mais relevantes por inscritos — Podpah, Flow Podcast,
Inteligência Ltda, AchismosTV, TICARACATICAST), reduzido de uma lista original
de 19. Motivo real, não estético: medi contra um Turso de verdade e cada escrita
custa um round-trip de rede (~0,2s, mesmo em lote — `sqlalchemy-libsql` ainda não
implementa o batching nativo do protocolo Hrana pra INSERT). Os 19 canais
completos somam ~46 mil vídeos → **horas** por execução; os 5 mais relevantes
somam ~19,5 mil → minutos a ~1h. `src/database.py::upsert_videos_scd2_batch`
ainda assim faz 1 SELECT por canal em vez de 1 por vídeo (o ganho real que deu
pra conseguir) — lista de canais e o porquê de cada um em `src/config.py`.

Roda automaticamente todo dia via **GitHub Actions**
(`.github/workflows/podcasts-ingest.yml`, cron `0 6 * * *` + disparo manual),
escrevendo direto num banco **Turso** — o runner do Actions é efêmero, não tem
onde persistir um arquivo local entre execuções, e é assim que o SCD2 finalmente
acumula histórico de verdade em vez de depender de coletas manuais esporádicas.

Acesse pela aba **Podcasts BR** do dashboard, ou rode localmente:

```bash
# Modo local (padrão) — grava em data/youtube.db, igual sempre foi:
python -m src.main
cd dbt && dbt run && dbt test

# Modo Turso (mesmo store usado no Actions) — preencha DB_BACKEND=turso,
# TURSO_DATABASE_URL e TURSO_AUTH_TOKEN no .env (turso db create / turso db
# tokens create), depois:
python -m src.main                    # escreve direto no Turso
pip install -r dbt/requirements.txt
python dbt/sync_replica.py            # espelha o Turso pra data/youtube.db local
cd dbt && dbt run && dbt test          # dbt-sqlite só lê arquivo local, nunca o Turso direto

python -m src.ranking --by views --shorts
```

Detalhes de ingestão (retry/backoff, tolerância a falha por canal), SCD2 e Docker
desse fluxo estão comentados no código (`src/database.py`, `src/main.py`,
`docker-compose.yml`, profiles `ingest`/`dbt`).

## Por que dois stores (DuckDB pra Copa, Turso pra podcasts)

Não é acaso — é o padrão de acesso de cada análise que decide:

- **Copa 2026 → DuckDB**: coleta **única**, batch, analítica — carrega tudo,
  faz joins/window functions pesados em memória, persiste o resultado uma vez.
  Perfil clássico de OLAP local, DuckDB é feito pra isso.
- **Podcasts → Turso (libSQL)**: coleta **recorrente** (diária, via cron), muitas
  escritas pequenas ao longo do tempo (um upsert SCD2 por canal/vídeo a cada
  run), rodando num runner efêmero que não tem disco persistente entre execuções.
  Perfil transacional clássico de OLTP — precisa de um store gerenciado que
  sobreviva entre execuções, não um arquivo local que o Actions apagaria a cada
  vez.

`dbt-sqlite` só fala SQLite local via `sqlite3` — não existe adapter dbt pra
libSQL remoto. Por isso `dbt/sync_replica.py` espelha as tabelas do Turso pra um
arquivo local (via SQLAlchemy Core, reaproveitando o schema de `Base.metadata`
em `src/database.py`) antes de cada `dbt run` — a leitura do dbt nunca muda
(`dbt/profiles.yml` aponta pro arquivo local sempre, venha ele de onde vier).

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
- [x] Store gerenciado (Turso/libSQL) pra podcasts, configurável por env var
      (`DB_BACKEND`), com fallback local pra dev
- [x] Agendar a ingestão de podcasts (cron / GitHub Actions) pra alimentar o
      histórico SCD2 automaticamente
- [ ] Expandir a análise da Copa pra outros eventos datados (eleições, Olimpíadas)
