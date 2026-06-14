-- DDL canônico do youtube_counter (documentação).
-- O schema real é criado em runtime pelo SQLAlchemy (database.init_db);
-- este arquivo serve como referência legível do modelo dimensional.

-- ===== Dimensões (SCD2) =====

CREATE TABLE dim_channel (
    channel_key        INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id         TEXT    NOT NULL,            -- chave natural (UC...)
    name               TEXT,
    handle             TEXT,
    country            TEXT,
    channel_created_at TEXT,
    valid_from         TIMESTAMP NOT NULL,
    valid_to           TIMESTAMP,                   -- NULL = versão vigente
    is_current         BOOLEAN NOT NULL DEFAULT 1
);
CREATE INDEX ix_dim_channel_current ON dim_channel (channel_id, is_current);

CREATE TABLE dim_video (
    video_key        INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id         TEXT    NOT NULL,              -- chave natural
    channel_id       TEXT    NOT NULL,
    title            TEXT,
    video_type       TEXT,                          -- 'short' | 'long' (derivado da duração)
    duration_seconds INTEGER,
    category_id      TEXT,
    default_language TEXT,
    definition       TEXT,                          -- 'hd' | 'sd'
    has_caption      BOOLEAN,
    tags             TEXT,                          -- JSON serializado
    published_at     TEXT,
    valid_from       TIMESTAMP NOT NULL,
    valid_to         TIMESTAMP,
    is_current       BOOLEAN NOT NULL DEFAULT 1
);
CREATE INDEX ix_dim_video_current ON dim_video (video_id, is_current);
CREATE INDEX ix_dim_video_channel ON dim_video (channel_id);

-- ===== Fatos (snapshot periódico) =====

CREATE TABLE fact_channel_metrics (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id       TEXT    NOT NULL,
    channel_key      INTEGER NOT NULL REFERENCES dim_channel (channel_key),
    collected_at     TIMESTAMP NOT NULL,
    subscriber_count INTEGER,
    total_views      INTEGER,
    video_count      INTEGER
);
CREATE INDEX ix_fact_channel_collected ON fact_channel_metrics (channel_id, collected_at);

CREATE TABLE fact_video_metrics (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id     TEXT    NOT NULL,
    video_key    INTEGER NOT NULL REFERENCES dim_video (video_key),
    collected_at TIMESTAMP NOT NULL,
    views        INTEGER,
    likes        INTEGER,
    comments     INTEGER,
    favorites    INTEGER
);
CREATE INDEX ix_fact_video_collected ON fact_video_metrics (video_id, collected_at);

-- As views analíticas estão em src/views.sql.
