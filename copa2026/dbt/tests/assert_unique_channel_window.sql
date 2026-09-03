-- Grão de channel_window_metrics deve ser (channel_id, window). Teste passa se não
-- retornar linhas.
select channel_id, time_window, count(*) as n
from {{ ref('channel_window_metrics') }}
group by channel_id, time_window
having count(*) > 1
