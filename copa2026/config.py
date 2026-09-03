"""Configuração da análise "Copa 2026": canais, janelas de data e caminho do DuckDB.

Reaproveita `src.config` para credenciais/logging — não duplica nada daquilo.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "copa2026.duckdb"

# Canais que transmitiram/cobriram a Copa do Mundo 2026 no Brasil.
# Handles validados no primeiro lookup real (get_channel_full) — 3 dos 5 originais
# estavam errados/duplicados, corrigidos aqui como já é feito pros handles de
# podcast em src/config.py:
#   - "GE TV" e "ge" eram o mesmo canal (@getv, 19,9M inscritos) — removida a
#     entrada duplicada.
#   - "N Sports": @NSPORTS_OFICIAL não existe; o canal real (811 mil inscritos) é
#     @nsports.
#   - "SporTV": @sportv não existe e a busca não achou canal próprio grande da
#     SporTV no YouTube. Substituído por TNT Sports Brasil (@tntsportsbr, 13,2M
#     inscritos, transmite esportes ao vivo) — alternativa que o próprio usuário
#     já tinha cogitado.
CHANNELS: list[str] = [
    "@CazeTV",
    "@getv",
    "@nsports",
    "@tntsportsbr",
]

# Janelas de análise (datas fixas, já no passado — permite coleta única e retroativa).
PRE_COPA = (date(2026, 5, 1), date(2026, 6, 10))
COPA = (date(2026, 6, 11), date(2026, 7, 19))  # abertura -> final
POS_COPA = (date(2026, 7, 20), date(2026, 8, 31))

# Intervalo total: usado pra saber onde parar a paginação da uploads playlist
# (mais antigo) e onde cortar os vídeos coletados (mais recente).
ANALYSIS_START = PRE_COPA[0]
ANALYSIS_END = POS_COPA[1]
