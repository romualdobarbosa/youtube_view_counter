-- Cast + métricas derivadas + classificação de janela (Pré-Copa/Copa/Pós-Copa).
-- A ingestão (copa2026/ingest.py) só grava o fato flat; a fronteira de datas de
-- cada janela é regra de negócio e fica aqui, não no lado da coleta.
select
    channel_id,
    channel_name,
    handle,
    video_id,
    title,
    cast(published_at as date) as published_date,
    duration_seconds,
    views,
    likes,
    comments,
    cast(likes + comments as double) / nullif(views, 0) as engagement_rate,
    case
        when cast(published_at as date)
            between date '{{ var("pre_copa_start") }}' and date '{{ var("pre_copa_end") }}'
            then 'Pré-Copa'
        when cast(published_at as date)
            between date '{{ var("copa_start") }}' and date '{{ var("copa_end") }}'
            then 'Copa'
        when cast(published_at as date)
            between date '{{ var("pos_copa_start") }}' and date '{{ var("pos_copa_end") }}'
            then 'Pós-Copa'
    end as time_window
from {{ source('raw', 'copa_videos') }}
