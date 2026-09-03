-- Crescimento de canal entre coletas consecutivas (inscritos / views totais).
with seq as (
    select
        f.channel_id,
        f.collected_at,
        f.subscriber_count,
        f.total_views,
        f.video_count,
        lag(f.subscriber_count) over w as prev_subscribers,
        lag(f.total_views)      over w as prev_total_views,
        lag(f.collected_at)     over w as prev_collected_at
    from {{ ref('stg_channel_metrics') }} f
    window w as (partition by f.channel_id order by f.collected_at)
)

select
    s.channel_id,
    c.name,
    s.prev_collected_at,
    s.collected_at,
    s.subscriber_count,
    s.subscriber_count - s.prev_subscribers as subscriber_delta,
    s.total_views,
    s.total_views - s.prev_total_views      as total_views_delta
from seq s
left join {{ ref('stg_channels') }} c
    on c.channel_id = s.channel_id
where s.prev_collected_at is not null
order by s.channel_id, s.collected_at
