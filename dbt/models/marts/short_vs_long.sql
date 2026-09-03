-- Short vs Long por canal: prova a tese de que vídeos curtos (verticais) capturam
-- uma fatia de views desproporcional ao seu tamanho no catálogo de podcasts longos.
with per_type as (
    select
        v.channel_id,
        c.name,
        v.video_type,
        count(*)               as videos,
        sum(v.views)           as total_views,
        avg(v.views)           as avg_views,
        avg(v.engagement_rate) as avg_engagement_rate
    from {{ ref('latest_video_metrics') }} v
    join {{ ref('stg_channels') }} c
        on c.channel_id = v.channel_id
    group by v.channel_id, c.name, v.video_type
),

totals as (
    select channel_id,
           sum(videos)      as all_videos,
           sum(total_views) as all_views
    from per_type
    group by channel_id
)

select
    p.channel_id,
    p.name,
    p.video_type,
    p.videos,
    cast(p.videos as real)      / nullif(t.all_videos, 0) as catalog_share,
    p.total_views,
    cast(p.total_views as real) / nullif(t.all_views, 0)  as views_share,
    p.avg_views,
    p.avg_engagement_rate
from per_type p
join totals t on t.channel_id = p.channel_id
order by p.channel_id, p.video_type
