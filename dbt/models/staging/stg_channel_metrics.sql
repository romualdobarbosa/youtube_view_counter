-- Pass-through do fato de snapshot de canal (renomeação/organização, sem regra de negócio).
select
    id,
    channel_id,
    channel_key,
    collected_at,
    subscriber_count,
    total_views,
    video_count
from {{ source('raw', 'fact_channel_metrics') }}
