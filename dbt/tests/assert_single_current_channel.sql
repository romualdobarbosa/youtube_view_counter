-- Invariante SCD2 que src/database.py::upsert_channel_scd2 já garante em código:
-- no máximo uma linha is_current = 1 por channel_id. Teste passa se não retornar linhas.
select channel_id, count(*) as current_rows
from {{ source('raw', 'dim_channel') }}
where is_current = 1
group by channel_id
having count(*) > 1
