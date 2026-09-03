-- Ranking por canal (a partir do último snapshot de cada vídeo).
select
    c.channel_id,
    c.name,
    c.handle,
    count(*)                                              as video_count,
    sum(v.views)                                          as total_views,
    avg(v.views)                                          as avg_views,
    avg(v.engagement_rate)                                as avg_engagement_rate,
    sum(case when v.video_type = 'short' then 1 else 0 end) as short_count,
    sum(case when v.video_type = 'long'  then 1 else 0 end) as long_count
from {{ ref('latest_video_metrics') }} v
join {{ ref('stg_channels') }} c
    on c.channel_id = v.channel_id
group by c.channel_id, c.name, c.handle
order by total_views desc
