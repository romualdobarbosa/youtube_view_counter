"""Configuração central: canais, caminhos, credenciais e logging."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Raiz do projeto (pasta que contém src/, data/, logs/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Caminho absoluto do banco — independente do cwd de onde o script é chamado.
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
DB_PATH = DATA_DIR / "youtube.db"

# Carrega variáveis do .env (se existir) e a chave da API.
load_dotenv(PROJECT_ROOT / ".env")


def get_api_key() -> str:
    """Retorna a YOUTUBE_API_KEY ou levanta erro com mensagem amigável."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError(
            "YOUTUBE_API_KEY não definida. Crie um arquivo .env (veja .env.example) "
            "ou exporte a variável de ambiente antes de rodar a ingestão."
        )
    return key


# Store da ingestão de podcasts: "local" (arquivo data/youtube.db, padrão — usado
# nos testes e no dev local) ou "turso" (banco gerenciado libSQL, necessário pra
# rodar via GitHub Actions, já que o runner é efêmero e não tem onde persistir um
# arquivo entre execuções).
DB_BACKEND = os.environ.get("DB_BACKEND", "local")
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")


def get_turso_credentials() -> tuple[str, str]:
    """Retorna (TURSO_DATABASE_URL, TURSO_AUTH_TOKEN) ou levanta erro amigável."""
    if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
        raise RuntimeError(
            "DB_BACKEND=turso mas TURSO_DATABASE_URL/TURSO_AUTH_TOKEN não estão "
            "definidos. Crie um banco Turso (turso db create ...) e preencha o "
            ".env (veja .env.example)."
        )
    return TURSO_DATABASE_URL, TURSO_AUTH_TOKEN


# Canais de podcast brasileiros. Aceita "@handle" ou "UCxxxx" — get_channel_full resolve os dois.
#
# Top 5 por inscritos (de uma lista original de 19 — reduzido pra caber num cron
# diário razoável rodando contra Turso: cada escrita é um round-trip de rede,
# ~0.2s/vídeo mesmo em lote — ver README > "Por que dois stores" e o commit que
# reduziu a lista. 19 canais = ~46 mil vídeos = horas por execução; os 5 abaixo =
# ~19.500 vídeos = minutos. Os mais relevantes (mais inscritos) ficaram.
CHANNELS: list[str] = [
    "@podpah",           # Podpah TV — 10,2M inscritos
    "@flowpodcast",      # Flow Podcast — 6,19M
    "@inteligencialtda", # Inteligência Ltda — 5,77M
    "@AchismosTV",       # AchismosTV — 5,44M (corrigido: @Achismos dava 404)
    "@Ticaracaticast",   # TICARACATICAST — 3,01M
]

# Vídeos com duração <= este limiar (segundos) são classificados como "short".
SHORT_MAX_SECONDS = 180


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configura logging para console + arquivo em logs/. Idempotente."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("youtube_counter")
    if logger.handlers:  # já configurado
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = logging.FileHandler(LOGS_DIR / "ingestion.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
