"""Espelha as 4 tabelas raw do Turso pra um arquivo SQLite local, pra o dbt-sqlite
(que só fala SQLite local via sqlite3, nunca libSQL remoto) ler um snapshot
recente antes de cada `dbt run`.

Regrava um arquivo SQLite comum com o driver stdlib do Python — nenhuma suposição
sobre formato de disco de embedded replicas do libSQL, só um DELETE+INSERT direto
via SQLAlchemy Core sobre o schema já definido em src/database.py.

Só faz algo quando DB_BACKEND=turso; em modo local, data/youtube.db já É o store
principal, nada a espelhar.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `python dbt/sync_replica.py` só põe dbt/ no sys.path, não a raiz do repo —
# precisa disso pra achar o pacote `src` (mesmo padrão de src/pages/*.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, insert

from src.config import DB_BACKEND, DB_PATH
from src.database import Base, get_engine


def main() -> None:
    if DB_BACKEND != "turso":
        print("DB_BACKEND != turso — nada a espelhar, dbt lê data/youtube.db direto.")
        return

    remote = get_engine()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    local = create_engine(f"sqlite:///{DB_PATH}", future=True)
    Base.metadata.create_all(local)

    with remote.connect() as rconn, local.begin() as lconn:
        for table in Base.metadata.sorted_tables:
            lconn.execute(table.delete())
            rows = rconn.execute(table.select()).mappings().all()
            if rows:
                lconn.execute(insert(table), [dict(r) for r in rows])
            print(f"  {table.name}: {len(rows)} linhas espelhadas")

    print(f"Réplica local sincronizada em {DB_PATH}")


if __name__ == "__main__":
    main()
