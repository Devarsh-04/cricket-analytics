select match_id, innings, over, ball_seq, count(*) as n
from {{ ref('stg_deliveries') }}
group by match_id, innings, over, ball_seq
having count(*) > 1
