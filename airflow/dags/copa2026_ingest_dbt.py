"""Ingestão + dbt da análise Copa do Mundo 2026 — substitui o disparo manual
via `docker compose --profile copa-ingest/copa-dbt run --rm ...`. Coleta
única e retroativa (não recorrente): schedule=None, disparo manual pela UI.

dbt roda numa venv própria (/usr/local/airflow/dbt_venvs/copa2026, construída
no Dockerfile), isolada do ambiente principal do Airflow e da venv do
projeto de podcasts — os dois pinam dbt-core em versões incompatíveis entre
si.

As tasks compartilham arquivo local (data/copa2026.duckdb, dentro de
/usr/local/airflow/repo/data/) pra passar dado entre elas — funciona aqui porque
`astro dev start` roda tudo num único container/worker; não é garantido em
produção com múltiplos workers (decisão de deploy, fora do escopo atual).
"""

from __future__ import annotations

from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task

REPO = "/usr/local/airflow/repo"
DBT_PROJECT = f"{REPO}/copa2026/dbt"
DBT_BIN = "/usr/local/airflow/dbt_venvs/copa2026/bin/dbt"


@dag(
    dag_id="copa2026_ingest_dbt",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["copa2026", "ingestao", "dbt"],
)
def copa2026_ingest_dbt():
    @task(retries=1)
    def ingest():
        from copa2026.ingest import run

        run()

    # cwd (não só --project-dir) importa aqui: profiles.yml resolve o
    # caminho relativo do duckdb (../../data/copa2026.duckdb) contra o cwd do
    # processo, não contra --project-dir — mesmo motivo pelo qual o
    # docker-compose roda com `cd copa2026/dbt && dbt run --profiles-dir .`.
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"{DBT_BIN} run --profiles-dir .",
        cwd=DBT_PROJECT,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"{DBT_BIN} test --profiles-dir .",
        cwd=DBT_PROJECT,
    )

    ingest() >> dbt_run >> dbt_test


copa2026_ingest_dbt()
