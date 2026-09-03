-- Pass-through do fato de snapshot de vídeo (renomeação/organização, sem regra de negócio).
select
    id,
    video_id,
    video_key,
    collected_at,
    views,
    likes,
    comments,
    favorites
from {{ source('raw', 'fact_video_metrics') }}
