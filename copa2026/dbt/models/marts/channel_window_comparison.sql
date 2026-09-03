-- Uma linha por canal: métricas das 3 janelas lado a lado + deltas que respondem
-- diretamente às duas perguntas da análise:
--   - Copa vs Pré-Copa: quem cresceu com a Copa?
--   - Pós-Copa vs Copa: quem reteve o engajamento depois que a Copa acabou?
with pivoted as (
    select
        channel_id,
        channel_name,
        max(case when time_window = 'Pré-Copa' then video_count end)         as pre_copa_videos,
        max(case when time_window = 'Pré-Copa' then total_views end)         as pre_copa_views,
        max(case when time_window = 'Pré-Copa' then avg_engagement_rate end) as pre_copa_engagement_rate,
        max(case when time_window = 'Copa' then video_count end)             as copa_videos,
        max(case when time_window = 'Copa' then total_views end)             as copa_views,
        max(case when time_window = 'Copa' then avg_engagement_rate end)     as copa_engagement_rate,
        max(case when time_window = 'Copa' then share_of_voice end)          as copa_share_of_voice,
        max(case when time_window = 'Pós-Copa' then video_count end)         as pos_copa_videos,
        max(case when time_window = 'Pós-Copa' then total_views end)         as pos_copa_views,
        max(case when time_window = 'Pós-Copa' then avg_engagement_rate end) as pos_copa_engagement_rate
    from {{ ref('channel_window_metrics') }}
    group by channel_id, channel_name
)

select
    channel_id,
    channel_name,
    pre_copa_videos,
    pre_copa_views,
    pre_copa_engagement_rate,
    copa_videos,
    copa_views,
    copa_engagement_rate,
    copa_share_of_voice,
    pos_copa_videos,
    pos_copa_views,
    pos_copa_engagement_rate,
    -- quem cresceu (Copa vs Pré)
    copa_views - pre_copa_views                                as views_growth_copa_vs_pre,
    (copa_views - pre_copa_views) / nullif(pre_copa_views, 0)   as views_growth_pct_copa_vs_pre,
    copa_engagement_rate - pre_copa_engagement_rate             as engagement_delta_copa_vs_pre,
    -- quem reteve (Pós vs Copa)
    pos_copa_views - copa_views                                 as views_delta_pos_vs_copa,
    pos_copa_engagement_rate - copa_engagement_rate              as engagement_delta_pos_vs_copa
from pivoted
order by copa_share_of_voice desc
