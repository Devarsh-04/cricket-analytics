select match_id, innings, over, ball_seq
from {{ ref('stg_deliveries') }}
where runs_total != runs_batter + runs_extras
