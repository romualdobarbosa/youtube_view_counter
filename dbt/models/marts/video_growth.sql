-- Velocity histórica: Δ views entre snapshots consecutivos de cada vídeo.
with seq as (
    select
        f.video_id,
        f.collected_at,
        f.views,
        lag(f.views)        over w as prev_views,
        lag(f.collected_at) over w as prev_collected_at
    from {{ ref('stg_video_metrics') }} f
    window w as (partition by f.video_id order by f.collected_at)
)

select
    s.video_id,
    d.title,
    d.channel_id,
    s.prev_collected_at,
    s.collected_at,
    s.views,
    s.views - s.prev_views as views_delta,
    (s.views - s.prev_views)
        / nullif(julianday(s.collected_at) - julianday(s.prev_collected_at), 0) as views_per_day_delta
from seq s
left join {{ ref('stg_videos') }} d
    on d.video_id = s.video_id
where s.prev_collected_at is not null
order by s.video_id, s.collected_at
