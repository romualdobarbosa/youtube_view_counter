-- A entrega principal: canal x janela x métricas.
-- share_of_voice = % das views totais do conjunto de canais naquela janela.
with per_channel_window as (
    select
        channel_id,
        channel_name,
        time_window,
        count(*)             as video_count,
        sum(views)           as total_views,
        avg(views)           as avg_views,
        avg(engagement_rate) as avg_engagement_rate
    from {{ ref('stg_copa_videos') }}
    where time_window is not null
    group by channel_id, channel_name, time_window
)

select
    channel_id,
    channel_name,
    time_window,
    video_count,
    total_views,
    avg_views,
    avg_engagement_rate,
    total_views / nullif(sum(total_views) over (partition by time_window), 0) as share_of_voice
from per_channel_window
order by time_window, total_views desc
