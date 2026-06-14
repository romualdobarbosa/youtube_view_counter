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


# Canais de podcast brasileiros. Aceita "@handle" ou "UCxxxx" — get_channel_full resolve os dois.
# IMPORTANTE: verifique os @handles antes da ingestão real. main.py é tolerante a falhas:
# um handle inexistente é logado e pulado, sem derrubar a coleta dos demais.
CHANNELS: list[str] = [
    "@flowpodcast",
    "@podpah",
    "@inteligencialtda",
    "@ossocios",  # corrigido: @ossociospodcast dava 404
    "@Ticaracaticast",
    "UCTBhsXf_XRxk8w4rMj6WBOA",  # Venus Podcast: handle @VenusPodcast não resolve; usando o ID do canal
    "@Poddelas",
    "@podcast3irmaos",  # corrigido: @3irmaospodcast dava 404
    "@CafecomDeusPai",
    "@Jovemnerd",
    "@quebrandootabu",
    "@PrimoCast",
    "@GroselhaTalk",
    "@naoinviabilize",
    "@AchismosTV",  # corrigido: @Achismos dava 404
    "@PodPeople",
    "@DevsCafe",
    "@HipstersPontoTech",
    "@cienciasemfim",
    "@JotaJotaPodcast",
    "@maoneca",
    "@PocCast",
    "@LinhasCruzadasOficial",
    "@modusoperandipodcast",
    "@papagaiopodcast",
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
