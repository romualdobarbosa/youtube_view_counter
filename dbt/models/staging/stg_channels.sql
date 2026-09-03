-- Versão vigente de cada canal (SCD2 filtrado em is_current).
select
    channel_key,
    channel_id,
    name,
    handle,
    country,
    channel_created_at
from {{ source('raw', 'dim_channel') }}
where is_current = 1
