FROM astrocrpublic.azurecr.io/runtime:3.1-1

# src/, copa2026/ e dbt/ (raiz do repo, fora do projeto Astro) chegam em
# include/repo/ via airflow/sync_repo_code.sh, que precisa rodar antes de
# `astro dev start`/`astro dev parse`. Copiados daqui pra /usr/local/airflow/repo
# (fora de include/) de propósito: em modo dev, `astro dev start` monta
# include/ como bind mount ao vivo (via virtiofs, dentro da VM do podman) —
# e esse mount não obedece chmod normalmente, então qualquer diretório que o
# código precise CRIAR em runtime (data/, logs/) dentro de include/ dá
# PermissionError. Copiando pra fora de include/, o diretório fica gravado na
# camada da imagem (sempre gravável pelo usuário astro), sem esse problema.
# Preserva a mesma estrutura de irmãos que o código já assume (dbt/sync_replica.py
# insere o parent.parent dele no sys.path; src/config.py calcula PROJECT_ROOT a
# partir de __file__) — a raiz vira /usr/local/airflow/repo, não colide com o
# logs/ que o próprio Airflow já usa em AIRFLOW_HOME.
COPY --chown=astro:0 include/repo/ /usr/local/airflow/repo/
ENV PYTHONPATH="/usr/local/airflow/repo:${PYTHONPATH}"

# Uma venv por projeto dbt, isolada do ambiente principal do Airflow e uma da
# outra — os dois pinam dbt-core em versões incompatíveis (ver
# include/repo/dbt/requirements.txt e include/repo/copa2026/dbt/requirements.txt).
# Construídas em build-time (não por task) por serem bem mais rápidas de usar
# do que criar uma venv do zero a cada execução.
RUN python -m venv /usr/local/airflow/dbt_venvs/podcasts && \
    /usr/local/airflow/dbt_venvs/podcasts/bin/pip install --no-cache-dir \
      dbt-core==1.11.14 dbt-adapters==1.16.7 dbt-sqlite==1.10.0
RUN python -m venv /usr/local/airflow/dbt_venvs/copa2026 && \
    /usr/local/airflow/dbt_venvs/copa2026/bin/pip install --no-cache-dir \
      dbt-core==1.12.3 dbt-adapters==1.24.5 dbt-duckdb==1.11.0 duckdb==1.5.5
