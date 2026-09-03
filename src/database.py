"""Modelos ORM (dimensional + SCD2), upserts e inicialização do banco."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import DATA_DIR, DB_PATH, SHORT_MAX_SECONDS


class Base(DeclarativeBase):
    pass


class DimChannel(Base):
    __tablename__ = "dim_channel"

    channel_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    handle: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String)
    channel_created_at: Mapped[str | None] = mapped_column(String)
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (Index("ix_dim_channel_current", "channel_id", "is_current"),)


class DimVideo(Base):
    __tablename__ = "dim_video"

    video_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String, nullable=False)
    channel_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    video_type: Mapped[str | None] = mapped_column(String)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    category_id: Mapped[str | None] = mapped_column(String)
    default_language: Mapped[str | None] = mapped_column(String)
    definition: Mapped[str | None] = mapped_column(String)
    has_caption: Mapped[bool | None] = mapped_column(Boolean)
    tags: Mapped[str | None] = mapped_column(Text)  # JSON serializado
    published_at: Mapped[str | None] = mapped_column(String)
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_dim_video_current", "video_id", "is_current"),
        Index("ix_dim_video_channel", "channel_id"),
    )


class FactChannelMetrics(Base):
    __tablename__ = "fact_channel_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String, nullable=False)
    channel_key: Mapped[int] = mapped_column(Integer, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    subscriber_count: Mapped[int | None] = mapped_column(Integer)
    total_views: Mapped[int | None] = mapped_column(Integer)
    video_count: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (Index("ix_fact_channel_collected", "channel_id", "collected_at"),)


class FactVideoMetrics(Base):
    __tablename__ = "fact_video_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String, nullable=False)
    video_key: Mapped[int] = mapped_column(Integer, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    views: Mapped[int | None] = mapped_column(Integer)
    likes: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[int | None] = mapped_column(Integer)
    favorites: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (Index("ix_fact_video_collected", "video_id", "collected_at"),)


# --- engine / session ---------------------------------------------------------

_engine: Engine | None = None


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Liga FK enforcement em toda conexão SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
    return _engine


def get_session() -> Session:
    return sessionmaker(bind=get_engine(), future=True)()


def init_db() -> None:
    """Cria as tabelas raw (dims SCD2 + fatos de snapshot).

    A camada semântica (views analíticas) não é mais criada aqui — é responsabilidade
    do projeto dbt em dbt/ (ver dbt/models/), que lê essas tabelas como source.
    """
    Base.metadata.create_all(get_engine())


# --- helpers SCD2 -------------------------------------------------------------

def _video_type(duration_seconds: int | None) -> str:
    if duration_seconds is not None and duration_seconds <= SHORT_MAX_SECONDS:
        return "short"
    return "long"


def upsert_channel_scd2(session: Session, data: dict[str, Any], now: datetime) -> int:
    """Insere/versiona um canal (SCD2). Retorna o channel_key vigente."""
    versioned = ("name", "handle", "country")
    current = session.scalars(
        select(DimChannel).where(
            DimChannel.channel_id == data["channel_id"],
            DimChannel.is_current.is_(True),
        )
    ).first()

    if current is not None:
        if all(getattr(current, f) == data.get(f) for f in versioned):
            return current.channel_key
        current.valid_to = now
        current.is_current = False

    new_row = DimChannel(
        channel_id=data["channel_id"],
        name=data.get("name"),
        handle=data.get("handle"),
        country=data.get("country"),
        channel_created_at=data.get("channel_created_at"),
        valid_from=now,
        valid_to=None,
        is_current=True,
    )
    session.add(new_row)
    session.flush()  # garante channel_key
    return new_row.channel_key


def upsert_video_scd2(session: Session, data: dict[str, Any], now: datetime) -> int:
    """Insere/versiona um vídeo (SCD2). Retorna o video_key vigente."""
    tags_json = json.dumps(data.get("tags") or [], ensure_ascii=False)
    vtype = _video_type(data.get("duration_seconds"))

    versioned = {
        "title": data.get("title"),
        "video_type": vtype,
        "category_id": data.get("category_id"),
        "tags": tags_json,
    }

    current = session.scalars(
        select(DimVideo).where(
            DimVideo.video_id == data["video_id"],
            DimVideo.is_current.is_(True),
        )
    ).first()

    if current is not None:
        if all(getattr(current, f) == v for f, v in versioned.items()):
            return current.video_key
        current.valid_to = now
        current.is_current = False

    new_row = DimVideo(
        video_id=data["video_id"],
        channel_id=data.get("channel_id"),
        title=versioned["title"],
        video_type=vtype,
        duration_seconds=data.get("duration_seconds"),
        category_id=versioned["category_id"],
        default_language=data.get("default_language"),
        definition=data.get("definition"),
        has_caption=data.get("has_caption"),
        tags=tags_json,
        published_at=data.get("published_at"),
        valid_from=now,
        valid_to=None,
        is_current=True,
    )
    session.add(new_row)
    session.flush()  # garante video_key
    return new_row.video_key


def insert_channel_metrics(
    session: Session, channel_key: int, data: dict[str, Any], collected_at: datetime
) -> None:
    session.add(
        FactChannelMetrics(
            channel_id=data["channel_id"],
            channel_key=channel_key,
            collected_at=collected_at,
            subscriber_count=data.get("subscriber_count"),
            total_views=data.get("total_views"),
            video_count=data.get("video_count"),
        )
    )


def insert_video_metrics(
    session: Session, video_key: int, data: dict[str, Any], collected_at: datetime
) -> None:
    session.add(
        FactVideoMetrics(
            video_id=data["video_id"],
            video_key=video_key,
            collected_at=collected_at,
            views=data.get("views"),
            likes=data.get("likes"),
            comments=data.get("comments"),
            favorites=data.get("favorites"),
        )
    )
