-- Último snapshot por vídeo, enriquecido com a dimensão vigente e métricas derivadas.
with ranked as (
    select
        f.*,
        row_number() over (partition by f.video_id order by f.collected_at desc) as rn
    from {{ ref('stg_video_metrics') }} f
)

select
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
    cast(r.likes + r.comments as real) / nullif(r.views, 0)        as engagement_rate,
    cast(r.likes as real)            / nullif(r.views, 0)          as like_rate,
    cast(r.comments as real)         / nullif(r.views, 0)          as comment_rate,
    julianday('now') - julianday(d.published_at)                  as days_since_publish,
    cast(r.views as real)
        / nullif(julianday('now') - julianday(d.published_at), 0) as views_per_day
from ranked r
join {{ ref('stg_videos') }} d
    on d.video_id = r.video_id
where r.rn = 1
