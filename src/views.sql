-- Camada analítica do youtube_counter.
-- Views idempotentes (CREATE VIEW IF NOT EXISTS) sobre dims SCD2 + fatos de snapshot.

-- Último snapshot por vídeo, enriquecido com a dimensão vigente e métricas derivadas.
CREATE VIEW IF NOT EXISTS v_latest_video_metrics AS
WITH ranked AS (
    SELECT
        f.*,
        ROW_NUMBER() OVER (PARTITION BY f.video_id ORDER BY f.collected_at DESC) AS rn
    FROM fact_video_metrics f
)
SELECT
    d.video_id,
    d.channel_id,
    d.title,
    d.video_type,
    d.duration_seconds,
    d.category_id,
    d.published_at,
    r.collected_at,
    r.views,
    r.likes,
    r.comments,
    r.favorites,
    CAST(r.likes + r.comments AS REAL) / NULLIF(r.views, 0)        AS engagement_rate,
    CAST(r.likes AS REAL)            / NULLIF(r.views, 0)          AS like_rate,
    CAST(r.comments AS REAL)         / NULLIF(r.views, 0)          AS comment_rate,
    julianday('now') - julianday(d.published_at)                  AS days_since_publish,
    CAST(r.views AS REAL)
        / NULLIF(julianday('now') - julianday(d.published_at), 0) AS views_per_day
FROM ranked r
JOIN dim_video d
    ON d.video_id = r.video_id AND d.is_current = 1
WHERE r.rn = 1;

-- Ranking por canal (a partir do último snapshot de cada vídeo).
CREATE VIEW IF NOT EXISTS v_channel_ranking AS
SELECT
    c.channel_id,
    c.name,
    c.handle,
    COUNT(*)                                              AS video_count,
    SUM(v.views)                                          AS total_views,
    AVG(v.views)                                          AS avg_views,
    AVG(v.engagement_rate)                                AS avg_engagement_rate,
    SUM(CASE WHEN v.video_type = 'short' THEN 1 ELSE 0 END) AS short_count,
    SUM(CASE WHEN v.video_type = 'long'  THEN 1 ELSE 0 END) AS long_count
FROM v_latest_video_metrics v
JOIN dim_channel c
    ON c.channel_id = v.channel_id AND c.is_current = 1
GROUP BY c.channel_id, c.name, c.handle
ORDER BY total_views DESC;

-- Crescimento de canal entre coletas consecutivas (inscritos / views totais).
CREATE VIEW IF NOT EXISTS v_channel_growth AS
WITH seq AS (
    SELECT
        f.channel_id,
        f.collected_at,
        f.subscriber_count,
        f.total_views,
        f.video_count,
        LAG(f.subscriber_count) OVER w AS prev_subscribers,
        LAG(f.total_views)      OVER w AS prev_total_views,
        LAG(f.collected_at)     OVER w AS prev_collected_at
    FROM fact_channel_metrics f
    WINDOW w AS (PARTITION BY f.channel_id ORDER BY f.collected_at)
)
SELECT
    s.channel_id,
    c.name,
    s.prev_collected_at,
    s.collected_at,
    s.subscriber_count,
    s.subscriber_count - s.prev_subscribers AS subscriber_delta,
    s.total_views,
    s.total_views - s.prev_total_views      AS total_views_delta
FROM seq s
LEFT JOIN dim_channel c
    ON c.channel_id = s.channel_id AND c.is_current = 1
WHERE s.prev_collected_at IS NOT NULL
ORDER BY s.channel_id, s.collected_at;

-- Velocity histórica: Δ views entre snapshots consecutivos de cada vídeo.
CREATE VIEW IF NOT EXISTS v_video_growth AS
WITH seq AS (
    SELECT
        f.video_id,
        f.collected_at,
        f.views,
        LAG(f.views)        OVER w AS prev_views,
        LAG(f.collected_at) OVER w AS prev_collected_at
    FROM fact_video_metrics f
    WINDOW w AS (PARTITION BY f.video_id ORDER BY f.collected_at)
)
SELECT
    s.video_id,
    d.title,
    d.channel_id,
    s.prev_collected_at,
    s.collected_at,
    s.views,
    s.views - s.prev_views AS views_delta,
    (s.views - s.prev_views)
        / NULLIF(julianday(s.collected_at) - julianday(s.prev_collected_at), 0) AS views_per_day_delta
FROM seq s
LEFT JOIN dim_video d
    ON d.video_id = s.video_id AND d.is_current = 1
WHERE s.prev_collected_at IS NOT NULL
ORDER BY s.video_id, s.collected_at;

-- Short vs Long por canal: prova a tese de que vídeos curtos (verticais) capturam
-- uma fatia de views desproporcional ao seu tamanho no catálogo de podcasts longos.
CREATE VIEW IF NOT EXISTS v_short_vs_long AS
WITH per_type AS (
    SELECT
        v.channel_id,
        c.name,
        v.video_type,
        COUNT(*)              AS videos,
        SUM(v.views)          AS total_views,
        AVG(v.views)          AS avg_views,
        AVG(v.engagement_rate) AS avg_engagement_rate
    FROM v_latest_video_metrics v
    JOIN dim_channel c
        ON c.channel_id = v.channel_id AND c.is_current = 1
    GROUP BY v.channel_id, c.name, v.video_type
),
totals AS (
    SELECT channel_id,
           SUM(videos)      AS all_videos,
           SUM(total_views) AS all_views
    FROM per_type
    GROUP BY channel_id
)
SELECT
    p.channel_id,
    p.name,
    p.video_type,
    p.videos,
    CAST(p.videos AS REAL)      / NULLIF(t.all_videos, 0) AS catalog_share,
    p.total_views,
    CAST(p.total_views AS REAL) / NULLIF(t.all_views, 0)  AS views_share,
    p.avg_views,
    p.avg_engagement_rate
FROM per_type p
JOIN totals t ON t.channel_id = p.channel_id
ORDER BY p.channel_id, p.video_type;

-- Cadência de upload e desempenho por dia da semana de publicação.
CREATE VIEW IF NOT EXISTS v_upload_cadence AS
SELECT
    channel_id,
    CAST(strftime('%w', published_at) AS INTEGER) AS weekday,  -- 0=domingo
    COUNT(*)      AS uploads,
    AVG(views)    AS avg_views,
    AVG(engagement_rate) AS avg_engagement_rate
FROM v_latest_video_metrics
WHERE published_at IS NOT NULL
GROUP BY channel_id, weekday
ORDER BY channel_id, weekday;
