"""Fixtures compartilhadas: isola cada teste num SQLite temporário próprio."""

from __future__ import annotations

import logging

import pytest

from src import config, database


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Substitui o banco e os logs reais por versões temporárias, descartadas ao fim do teste."""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "LOGS_DIR", tmp_path / "logs")
    database._engine = None
    logger = logging.getLogger("youtube_counter")
    logger.handlers.clear()
    yield
    database._engine = None
    logger.handlers.clear()
