-- Invariante SCD2 que src/database.py::upsert_video_scd2 já garante em código:
-- no máximo uma linha is_current = 1 por video_id. Teste passa se não retornar linhas.
select video_id, count(*) as current_rows
from {{ source('raw', 'dim_video') }}
where is_current = 1
group by video_id
having count(*) > 1
