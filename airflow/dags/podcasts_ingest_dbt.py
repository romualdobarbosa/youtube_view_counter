"""Ingestão + dbt dos canais de podcast — substitui o cron do GitHub Actions
(.github/workflows/podcasts-ingest.yml). Mesmo schedule (06:00 UTC), mesmos
passos: ingest -> sync Turso->SQLite -> dbt run -> dbt test.

dbt roda numa venv própria (/usr/local/airflow/dbt_venvs/podcasts, construída
no Dockerfile), isolada do ambiente principal do Airflow e da venv do projeto
Copa 2026 — os dois pinam dbt-core em versões incompatíveis entre si.

As tasks compartilham arquivo local (data/youtube.db, dentro de
/usr/local/airflow/repo/data/) pra passar dado entre elas — funciona aqui porque
`astro dev start` roda tudo num único container/worker; não é garantido em
produção com múltiplos workers (decisão de deploy, fora do escopo atual).
"""

from __future__ import annotations

from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task

REPO = "/usr/local/airflow/repo"
DBT_PROJECT = f"{REPO}/dbt"
DBT_BIN = "/usr/local/airflow/dbt_venvs/podcasts/bin/dbt"


@dag(
    dag_id="podcasts_ingest_dbt",
    schedule="0 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["podcasts", "ingestao", "dbt"],
)
def podcasts_ingest_dbt():
    @task(retries=1)
    def ingest():
        from src.main import run

        run()

    @task
    def sync_turso_to_sqlite():
        from dbt.sync_replica import main

        main()

    # cwd (não só --project-dir) importa aqui: profiles.yml resolve os
    # caminhos relativos do banco (../data/youtube.db) contra o cwd do
    # processo, não contra --project-dir — mesmo motivo pelo qual o
    # docker-compose roda com `cd dbt && dbt run --profiles-dir .`.
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

    ingest() >> sync_turso_to_sqlite() >> dbt_run >> dbt_test


podcasts_ingest_dbt()
