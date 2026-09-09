#!/usr/bin/env bash
# Espelha src/, copa2026/ e dbt/ (raiz do repo, fora do projeto Astro) para
# airflow/include/repo/ antes de `astro dev start`/`astro dev parse`/`astro
# deploy` — esses comandos só enxergam arquivos dentro de airflow/ (build
# context do projeto Astro), então isso precisa rodar antes de qualquer um
# deles. airflow/include/repo/ é gerado (gitignored), nunca editar direto lá.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_ROOT/airflow/include/repo"

mkdir -p "$DEST"
EXCLUDES=(--exclude='__pycache__' --exclude='target' --exclude='logs' --exclude='dbt_packages' --exclude='.user.yml')
rsync -a --delete "${EXCLUDES[@]}" "$REPO_ROOT/src/" "$DEST/src/"
rsync -a --delete "${EXCLUDES[@]}" "$REPO_ROOT/copa2026/" "$DEST/copa2026/"
rsync -a --delete "${EXCLUDES[@]}" "$REPO_ROOT/dbt/" "$DEST/dbt/"

echo "Sincronizado em $DEST"
