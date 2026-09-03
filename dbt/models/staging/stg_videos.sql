-- Versão vigente de cada vídeo (SCD2 filtrado em is_current).
select
    video_key,
    video_id,
    channel_id,
    title,
    video_type,
    duration_seconds,
    category_id,
    published_at
from {{ source('raw', 'dim_video') }}
where is_current = 1
