-- Cadência de upload e desempenho por dia da semana de publicação.
select
    channel_id,
    cast(strftime('%w', published_at) as integer) as weekday,  -- 0=domingo
    count(*)             as uploads,
    avg(views)            as avg_views,
    avg(engagement_rate)  as avg_engagement_rate
from {{ ref('latest_video_metrics') }}
where published_at is not null
group by channel_id, weekday
order by channel_id, weekday
